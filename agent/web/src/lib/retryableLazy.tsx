import {createContext, createElement, lazy, useContext, type ComponentProps, type ComponentType, type LazyExoticComponent} from 'react';

type RetryScope = {identity: object; generation: number};
const defaultScope: RetryScope = {identity: {}, generation: 0};
export const ViewLoadRetryContext = createContext<RetryScope>(defaultScope);

export class DeferredViewLoadError extends Error {
  constructor(readonly failure: unknown) {
    super('Le chargement de la rubrique a échoué.');
    this.name = 'DeferredViewLoadError';
  }
}

export function isStylesheetLoadFailure(error: unknown): boolean {
  return error instanceof DeferredViewLoadError && /Unable to preload CSS/i.test(String(error.failure));
}

/** A failed React.lazy promise is replaced only when its own view retries. */
// Match React.lazy's component constraint so named component props are inferred.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function retryableLazy<T extends ComponentType<any>>(load: () => Promise<{default: T}>, retry: () => Promise<{default: T}>): ComponentType<ComponentProps<T>> {
  const versions = new WeakMap<object, {generation: number; component: LazyExoticComponent<T>}>();
  return function RetryableView(props: ComponentProps<T>) {
    const scope = useContext(ViewLoadRetryContext);
    let entry = versions.get(scope.identity);
    if (!entry || entry.generation !== scope.generation) {
      const attempt = scope.generation === 0 ? load : retry;
      entry = {generation: scope.generation, component: lazy(() => attempt().catch(error => {throw new DeferredViewLoadError(error);}))};
      versions.set(scope.identity, entry);
    }
    return createElement(entry.component as unknown as ComponentType<ComponentProps<T>>, props);
  };
}
