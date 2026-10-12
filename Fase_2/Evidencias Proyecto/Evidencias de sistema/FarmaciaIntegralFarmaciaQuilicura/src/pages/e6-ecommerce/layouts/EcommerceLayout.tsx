import { Outlet } from 'react-router-dom'
import CartProvider from '../components/CartProvider'
import GuestProvider from '../components/GuestProvider'
import CustomerSessionProvider from '../components/CustomerSessionProvider'

export default function EcommerceLayout() { return <CustomerSessionProvider><CartProvider><GuestProvider><Outlet /></GuestProvider></CartProvider></CustomerSessionProvider> }
