const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { create, act } = require('react-test-renderer');

// Compile the actual components; replace only their API/context/UI boundaries.
function load(file, dependencies, globals = {}) {
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8').replaceAll('import.meta.env', '({})'), {
    fileName: file,
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const exports = {};
  vm.runInNewContext(code, {
    exports,
    ...globals,
    require: name => {
      if (name === 'react' || name === 'react/jsx-runtime') return require(name);
      if (name.endsWith('.css')) return {};
      if (dependencies[name]) return dependencies[name];
      throw new Error(`Unmocked import: ${name}`);
    },
  }, { filename: file });
  return exports;
}

test('only successful sends analyze; history, remounts and refresh do not; retry is specific', async () => {
  const calls = [];
  let failAnalysis = false;
  let failSend = false;
  const messages = Array.from({ length: 100 }, (_, i) => ({ id: `old-${i}`, member_id: 'me', content: 'clean up' }));
  const data = { data: messages, isLoading: false, error: null, reload() {} };
  const service = {
    list: async () => messages,
    create: async content => {
      if (failSend) throw new Error('offline');
      const message = { id: `new-${messages.length}`, member_id: 'me', content };
      messages.push(message);
      return message;
    },
    analyze: async id => {
      calls.push(id);
      if (failAnalysis) throw new Error('unavailable');
      return { message_id: id, is_task: true, suggestion: { title: 'Do dishes', assigned_to_id: null, due_date: null } };
    },
  };
  const noop = () => null;
  class ApiError extends Error {}
  const shared = {
    '../../services/api': { ApiError },
    '../../context/ToastContext': { useToast: () => ({ showToast() {} }) },
    '../../services/choreService': { choreService: { create: async () => assert.fail('No automatic chore creation') } },
    '../chores/AddChoreModal': { AddChoreModal: noop },
  };
  const { MessageChoreSuggestion } = load('src/components/chat/MessageChoreSuggestion.tsx', shared);
  const { ChatPage } = load('src/pages/ChatPage.tsx', {
    '../components/chat/MessageChoreSuggestion': { MessageChoreSuggestion },
    '../components/chat/ConnectionBadge': { ConnectionBadge: noop },
    '../components/chat/MessageBubble': { MessageBubble: noop },
    '../components/common/ui': { EmptyState: noop, ErrorState: noop, LoadingState: noop, PageHeader: noop },
    '../components/layout/icons': { SendIcon: noop },
    '../context/HouseholdContext': { useHousehold: () => ({ currentMember: { id: 'me' } }) },
    '../context/ToastContext': shared['../../context/ToastContext'],
    '../hooks/useApiData': { useApiData: () => data },
    '../services/messageService': { messageService: service },
    '../services/api': { ApiError },
  });
  let view;
  const render = () => React.createElement(React.StrictMode, null, React.createElement(ChatPage));
  await act(async () => { view = create(render()); });
  assert.deepEqual(calls, []);
  const update = async () => { await act(async () => view.update(render())); };
  await update();
  assert.deepEqual(calls, []);
  async function send(text) {
    act(() => view.root.findByType('textarea').props.onChange({ target: { value: text } }));
    await act(async () => view.root.findByProps({ 'aria-label': 'Send message' }).props.onClick());
  }
  await send('Please do the dishes');
  assert.deepEqual(calls, ['new-100']);
  await update();
  data.error = 'temporary history error';
  await update(); // Unmount the entire message list, then restore it.
  data.error = null;
  await update();
  assert.deepEqual(calls, ['new-100']);
  failAnalysis = true;
  await send('Water the plants');
  assert.deepEqual(calls, ['new-100', 'new-101']);
  failAnalysis = false;
  const retry = view.root.findAllByType('button').find(button => button.props.children === 'Retry analysis');
  await act(async () => retry.props.onClick());
  assert.deepEqual(calls, ['new-100', 'new-101', 'new-101']);
  failSend = true;
  await send('Not saved');
  assert.equal(calls.length, 3);
  act(() => view.unmount());
  await act(async () => { view = create(render()); }); // Page refresh with all messages now in history.
  assert.equal(calls.length, 3);
  act(() => view.unmount());
});


test('provider quota exhaustion shows no retry button and never creates a chore', async () => {
  class ApiError extends Error {}
  const error = new ApiError('provider quota');
  error.code = 'AI_PROVIDER_RATE_LIMITED';
  error.retryable = false;
  const { MessageChoreSuggestion } = load('src/components/chat/MessageChoreSuggestion.tsx', {
    '../../services/api': { ApiError },
    '../../context/ToastContext': { useToast: () => ({ showToast() {} }) },
    '../../services/choreService': { choreService: { create: () => assert.fail('Unexpected chore') } },
    '../chores/AddChoreModal': { AddChoreModal: () => null },
  });
  let view;
  await act(async () => {
    view = create(React.createElement(MessageChoreSuggestion, {
      messageId: 'quota-message', analysis: Promise.reject(error),
      onRetry: () => assert.fail('Unexpected retry'),
    }));
  });
  assert.equal(view.root.findAllByType('button').length, 0);
  assert.match(JSON.stringify(view.toJSON()), /quota limit/);
  act(() => view.unmount());
});

test('chore form preserves 9pm and does not invent a time for date-only suggestions', () => {
  const previousTZ = process.env.TZ;
  process.env.TZ = 'America/New_York';
  try {
    const { AddChoreModal } = load('src/components/chores/AddChoreModal.tsx', {
      '../../context/HouseholdContext': { useHousehold: () => ({ members: [] }) },
      '../common/Modal': { Modal: ({ children }) => children },
    });
    for (const [due_at, expected] of [['2026-09-20T21:00:00-04:00', '21:00'], [null, '']]) {
      let view;
      act(() => { view = create(React.createElement(AddChoreModal, {
        isOpen: true, onClose() {}, onSubmit() {},
        initialValues: { title: 'Dishes', assigned_to_id: null, due_date: '2026-09-20', due_at },
      })); });
      assert.equal(view.root.findByProps({ name: 'due-time' }).props.value, expected);
      assert.equal(view.root.findByProps({ name: 'due-date' }).props.value, '2026-09-20');
      act(() => view.unmount());
    }
  } finally {
    if (previousTZ === undefined) delete process.env.TZ;
    else process.env.TZ = previousTZ;
  }
});


test('invalid active session clears credentials and notifies household context', async () => {
  let token = 'expired';
  const events = [];
  const { api } = load('src/services/api.ts', {}, {
    window: { location: { origin: 'http://localhost' }, dispatchEvent: event => events.push(event.type) },
    localStorage: { getItem: () => token, removeItem: () => { token = null; } },
    Event,
    fetch: async () => ({ status: 401, ok: false, text: async () => '{"detail":"Invalid session"}' }),
  });
  await assert.rejects(api.get('/api/messages'));
  assert.equal(token, null);
  assert.deepEqual(events, ['liferoom:session-invalid']);
});
