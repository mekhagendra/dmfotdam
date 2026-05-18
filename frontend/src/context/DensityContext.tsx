import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type Density = 'comfortable' | 'compact';

interface DensityContextValue {
  density: Density;
  setDensity: (d: Density) => void;
  toggle: () => void;
}

const DensityContext = createContext<DensityContextValue | undefined>(undefined);

const STORAGE_KEY = 'tdm.density';

export const DensityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [density, setDensityState] = useState<Density>(() => {
    if (typeof window === 'undefined') return 'comfortable';
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'compact' ? 'compact' : 'comfortable';
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, density);
    document.documentElement.dataset.density = density;
  }, [density]);

  const setDensity = useCallback((d: Density) => setDensityState(d), []);
  const toggle = useCallback(
    () => setDensityState((prev) => (prev === 'comfortable' ? 'compact' : 'comfortable')),
    [],
  );

  return (
    <DensityContext.Provider value={{ density, setDensity, toggle }}>
      {children}
    </DensityContext.Provider>
  );
};

export function useDensity(): DensityContextValue {
  const ctx = useContext(DensityContext);
  if (!ctx) {
    // Safe fallback so components outside the provider still work.
    return {
      density: 'comfortable',
      setDensity: () => undefined,
      toggle: () => undefined,
    };
  }
  return ctx;
}
