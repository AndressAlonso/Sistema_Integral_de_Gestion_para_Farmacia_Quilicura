const paths = {
  chart: 'M4 19h16M6 15l4-5 4 3 5-8M15 5h4v4',
  branch: 'M3 21h18M5 21V4h14v17M9 8h2M13 8h2M9 12h2M13 12h2M10 21v-5h4v5',
  calendar: 'M5 5h14v16H5ZM8 3v4M16 3v4M5 10h14M8 14h2M14 14h2',
  refresh: 'M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2ZM9 7h6M9 11h6M9 15h3',
  box: 'm12 3 9 5-9 5-9-5 9-5ZM3 8v9l9 5 9-5V8M12 13v9',
  clock: 'M12 8v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  arrow: 'M5 12h14m-5-5 5 5-5 5',
  check: 'm5 12 4 4L19 6',
}
export default function MetricIcon({ name }: { name: keyof typeof paths }) {
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
