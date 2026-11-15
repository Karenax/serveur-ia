import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delay = 250) {
  const [current, setCurrent] = useState(value);
  useEffect(() => {const timer = window.setTimeout(() => setCurrent(value), delay); return () => window.clearTimeout(timer);}, [value, delay]);
  return current;
}
