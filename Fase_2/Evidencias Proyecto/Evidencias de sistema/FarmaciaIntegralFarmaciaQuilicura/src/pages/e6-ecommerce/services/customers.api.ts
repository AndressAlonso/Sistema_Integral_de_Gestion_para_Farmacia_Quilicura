import { apiRequest } from '../../../services/http'
import type { Customer, CustomerCredentials, CustomerRegistration, CustomerSession } from '../types/customer'

const messages = {
  401: 'Correo o contraseña incorrectos.',
  409: 'No se pudo registrar una cuenta con ese correo.',
  422: 'Revisa los datos ingresados. La contraseña debe tener entre 12 y 128 caracteres.',
}

export async function registerCustomer(data: CustomerRegistration): Promise<Customer> {
  return (await apiRequest('/api/customers/register', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }, messages)).json()
}

export async function loginCustomer(data: CustomerCredentials): Promise<CustomerSession> {
  return (await apiRequest('/api/customers/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  }, messages)).json()
}

export async function getCustomerSession(): Promise<CustomerSession> {
  return (await apiRequest('/api/customers/me')).json()
}

export async function logoutCustomer(): Promise<void> {
  await apiRequest('/api/customers/logout', { method: 'POST' })
}
