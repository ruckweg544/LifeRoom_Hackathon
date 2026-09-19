module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['react-hooks'],
  extends: ['plugin:react-hooks/recommended'],
  ignorePatterns: ['dist', 'node_modules'],
};
