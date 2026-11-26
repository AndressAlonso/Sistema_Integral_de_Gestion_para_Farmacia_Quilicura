import { useId, useLayoutEffect, useRef, useState, type SelectHTMLAttributes } from 'react'
import './select-menu.css'

type Option = { value: string; label: string; disabled: boolean }
/** Keeps native form submission and validation while presenting a themed picker. */
export default function SelectMenu(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const select = useRef<HTMLSelectElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const id = useId()
  const [open, setOpen] = useState(false)
  const [label, setLabel] = useState('')
  const [selected, setSelected] = useState('')
  const [invalid, setInvalid] = useState(false)
  const [accessibleName, setAccessibleName] = useState('')
  const [options, setOptions] = useState<Option[]>([])
  const [active, setActive] = useState(0)
  useLayoutEffect(() => {
    const element = select.current
    if (element) {
      setLabel(element.selectedOptions[0]?.textContent ?? ''); setSelected(element.value)
      const caption = element.closest('label')?.cloneNode(true) as HTMLElement | undefined
      caption?.querySelectorAll('.select-menu').forEach(node => node.remove())
      setAccessibleName(caption?.textContent?.trim() ?? '')
    }
  }, [props.value, props.defaultValue, props.children])
  function close() { panel.current?.hidePopover(); setOpen(false) }
  function show() {
    const element = select.current
    const popup = panel.current
    const button = trigger.current
    if (!element || !popup || !button || button.matches(':disabled')) return
    const rows = Array.from(element.options).map(option => ({ value: option.value, label: option.text, disabled: option.disabled || (option.parentElement instanceof HTMLOptGroupElement && option.parentElement.disabled) }))
    setOptions(rows)
    setActive(Math.max(0, element.selectedIndex))
    const rect = button.getBoundingClientRect()
    popup.style.width = `${Math.min(Math.max(rect.width, 200), window.innerWidth - 24)}px`
    popup.style.left = `${Math.max(12, Math.min(rect.left, window.innerWidth - Math.max(rect.width, 200) - 12))}px`
    const below = window.innerHeight - rect.bottom - 12
    popup.style.top = below >= 180 ? `${rect.bottom + 6}px` : 'auto'
    popup.style.bottom = below >= 180 ? 'auto' : `${window.innerHeight - rect.top + 6}px`
    popup.style.maxHeight = `${Math.max(100, Math.min(280, below >= 180 ? below - 6 : rect.top - 18))}px`
    popup.showPopover()
    setOpen(true)
  }
  function choose(index: number) {
    const element = select.current
    if (!element || !options[index] || options[index].disabled) return
    element.value = options[index].value
    element.dispatchEvent(new Event('change', { bubbles: true }))
    setLabel(options[index].label)
    setSelected(options[index].value)
    setInvalid(!element.validity.valid)
    close()
    trigger.current?.focus()
  }
  return <span className="select-menu">
    <select {...props} id={undefined} ref={select} className="select-menu-native" tabIndex={-1} aria-hidden="true" onInvalid={event => { event.preventDefault(); trigger.current?.focus(); setInvalid(true) }} />
    <button ref={trigger} id={props.id} type="button" className="select-menu-trigger" role="combobox" aria-expanded={open} aria-controls={id} aria-haspopup="listbox" aria-required={props.required} aria-invalid={invalid || undefined} aria-label={props['aria-label'] || accessibleName || undefined} aria-labelledby={props['aria-labelledby']} aria-describedby={props['aria-describedby']} disabled={props.disabled} onClick={() => open ? close() : show()} onKeyDown={event => {
      if (event.key === 'Escape' && open) { event.preventDefault(); close(); event.stopPropagation(); return }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        event.preventDefault()
        if (!open) { show(); return }
        const direction = event.key === 'ArrowUp' ? -1 : 1
        let next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : active + direction
        while (next >= 0 && next < options.length && options[next].disabled) next += direction
        if (next >= 0 && next < options.length) { setActive(next); panel.current?.children[next]?.scrollIntoView({ block: 'nearest' }) }
      } else if (open && ['Enter', ' '].includes(event.key)) { event.preventDefault(); choose(active) }
      else if (event.key === 'Tab') close()
      else if (event.key.length === 1 && open) { const next = options.findIndex(option => !option.disabled && option.label.toLocaleLowerCase().startsWith(event.key.toLocaleLowerCase())); if (next >= 0) setActive(next) }
    }} aria-activedescendant={open ? `${id}-${active}` : undefined}>
      <span>{label || 'Selecciona una opción'}</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
    </button>
    <div ref={panel} id={id} className="select-menu-panel" popover="auto" role="listbox" aria-label={props['aria-label'] || 'Opciones disponibles'} onToggle={event => { if (event.newState === 'closed') setOpen(false) }}>
      {options.map((option, index) => <div key={`${option.value}-${index}`} id={`${id}-${index}`} role="option" aria-selected={selected === option.value} aria-disabled={option.disabled} className={index === active ? 'is-active' : ''} onPointerDown={event => event.preventDefault()} onClick={() => choose(index)}>{option.label}{selected === option.value && <span aria-hidden="true">✓</span>}</div>)}
    </div>
    {invalid && <span className="select-menu-error" role="alert">Selecciona una opción.</span>}
  </span>
}
