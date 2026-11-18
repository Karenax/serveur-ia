// Vite compiles a second, independently fetchable copy of each deferred entry.
declare module '*?kiara-retry=1' {
  const module: unknown;
  export = module;
}
