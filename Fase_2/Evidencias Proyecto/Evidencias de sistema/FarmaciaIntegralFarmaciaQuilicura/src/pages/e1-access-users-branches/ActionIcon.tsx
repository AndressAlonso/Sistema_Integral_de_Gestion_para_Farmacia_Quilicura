const paths = {
  edit: 'm16 3 5 5-12 12-6 1 1-6L16 3ZM14 5l5 5',
  deactivate: 'M12 3v9M6.3 5.7a9 9 0 1 0 11.4 0',
  delete: 'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',
  add: 'M12 5v14M5 12h14',
}

export default function ActionIcon({ name }: { name: keyof typeof paths }) {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>
}
