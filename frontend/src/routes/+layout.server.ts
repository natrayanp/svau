import type { LayoutLoad, LayoutLoadEvent } from './$types';

export const load = (({ url }: LayoutLoadEvent) => {
  return {
    pathname: url.pathname
  };
}) satisfies LayoutLoad;

