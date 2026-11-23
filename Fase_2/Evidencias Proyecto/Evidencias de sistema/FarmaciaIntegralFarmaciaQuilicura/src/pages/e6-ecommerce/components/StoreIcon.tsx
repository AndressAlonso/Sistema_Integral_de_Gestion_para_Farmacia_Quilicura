const paths = {
  search: 'M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
  location: 'M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0M4 21v-2a8 8 0 0 1 16 0v2',
  orders: 'M4 6l8-4 8 4v12l-8 4-8-4V6ZM4 6l8 4 8-4M12 10v12M8 4l8 4',
  cart: 'M3 3h2l3 12h10l3-9H6M10 20a1 1 0 1 1-2 0 1 1 0 0 1 2 0M19 20a1 1 0 1 1-2 0 1 1 0 0 1 2 0',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2V3ZM9 7h6M9 11h6M9 15h3',
  mail: 'M3 5h18v14H3V5ZM3 5l9 7 9-7',
  lock: 'M5 10h14v11H5V10ZM8 10V7a4 4 0 0 1 8 0v3M12 14v3',
}

export default function StoreIcon({ name }: { name: keyof typeof paths }) {
  return <svg className="store-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>
}
