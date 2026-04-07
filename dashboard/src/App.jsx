import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { hasToken } from './api'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import DeviceDetail from './pages/DeviceDetail'
import Alerts from './pages/Alerts'

function PrivateRoute({ children }) {
    return hasToken() ? children : <Navigate to="/login" replace />
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/" element={
                    <PrivateRoute><Dashboard /></PrivateRoute>
                } />
                <Route path="/device/:id" element={
                    <PrivateRoute><DeviceDetail /></PrivateRoute>
                } />
                <Route path="/alerts" element={
                    <PrivateRoute><Alerts /></PrivateRoute>
                } />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    )
}