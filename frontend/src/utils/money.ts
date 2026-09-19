/** Formats integer cents as a USD string, e.g. 9000 -> "$90.00". Never do float math on money in components. */
export function formatCents(cents: number): string {
  const sign = cents < 0 ? "-" : "";
  return `${sign}$${(Math.abs(cents) / 100).toFixed(2)}`;
}

export function dollarsToCents(amount: number): number {
  return Math.round(amount * 100);
}
