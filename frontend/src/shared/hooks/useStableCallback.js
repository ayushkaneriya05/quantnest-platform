import {useCallback,useLayoutEffect,useRef} from 'react';

// Event/polling handlers retain one identity while reading the latest committed
// state. Reactive effects still list the IDs/filters that should trigger loads.
export function useStableCallback(callback) {
  const latest=useRef(callback);
  useLayoutEffect(()=>{latest.current=callback},[callback]);
  return useCallback((...args)=>latest.current(...args),[]);
}
