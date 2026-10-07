export interface Customer {
  id: string
  name: string
  email: string
}

export interface CustomerSession {
  customer: Customer
  expires_at: string
}

export interface CustomerCredentials {
  email: string
  password: string
}

export interface CustomerRegistration extends CustomerCredentials {
  name: string
}
