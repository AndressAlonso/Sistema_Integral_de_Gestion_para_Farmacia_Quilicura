import { fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, beforeAll, expect, it, vi } from 'vitest'
import SelectMenu from './SelectMenu'
beforeAll(() => {
  HTMLElement.prototype.showPopover = function () { this.style.display = "block" }
  HTMLElement.prototype.hidePopover = function () { this.style.display = "none" }
  HTMLElement.prototype.scrollIntoView = function () {}
})
afterEach(cleanup)
it('submits the chosen value and notifies the form', () => {
  const change = vi.fn()
  const { container } = render(<form><label>Sucursal<SelectMenu name="branch" defaultValue="a" onChange={change}><option value="a">Centro</option><option value="b">Norte</option></SelectMenu></label></form>)
  fireEvent.click(screen.getByRole('combobox', { name:'Sucursal' }))
  fireEvent.click(screen.getByRole('option', {name:'Norte'}))
  expect(change).toHaveBeenCalledOnce()
  expect(new FormData(container.querySelector('form')!).get('branch')).toBe('b')
})
it('supports keyboard selection and required validation', () => {
  const {container}=render(<label>Categoría<SelectMenu required defaultValue=""><option value="" disabled>Selecciona</option><option value="a">Salud</option></SelectMenu></label>)
  const button=screen.getByRole('combobox',{name:'Categoría'})
  fireEvent.invalid(container.querySelector('select')!)
  expect(button.getAttribute('aria-invalid')).toBe('true')
  fireEvent.keyDown(button,{key:'ArrowDown'})
  fireEvent.keyDown(button,{key:'ArrowDown'})
  fireEvent.keyDown(button,{key:'Enter'})
  expect(container.querySelector('select')!.value).toBe('a')
  expect(button.getAttribute('aria-invalid')).toBe(null)
})
