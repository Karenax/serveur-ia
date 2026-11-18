export const errorMessage = (error: unknown) => error instanceof Error ? error.message : String(error);
export const dateLabel = (value?: string | null) => {
  if (!value) return "Date non précisée";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("fr-FR", {day: "numeric", month: "short", year: "numeric"}).format(date);
};
