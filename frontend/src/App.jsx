import { Routes, Route, Navigate } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import Footer from "./components/Footer.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import ForgotPassword from "./pages/ForgotPassword.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import ProfileSetup from "./pages/ProfileSetup.jsx";
import MyEvents from "./pages/MyEvents.jsx";
import EventDirectory from "./pages/EventDirectory.jsx";
import SavedContacts from "./pages/SavedContacts.jsx";
import Discover from "./pages/Discover.jsx";
import Messages from "./pages/Messages.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import AdminEvents from "./pages/AdminEvents.jsx";
import AdminEventDetail from "./pages/AdminEventDetail.jsx";
import AdminTemplates from "./pages/AdminTemplates.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";
import JoinEvent from "./pages/JoinEvent.jsx";
import { useAuth } from "./hooks/useAuth.jsx";

export default function App() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Nav />
      <div className="pt-14 flex-1">
        <Routes>
          <Route
            path="/"
            element={
              <Navigate
                to={user ? (user.is_admin ? "/admin" : "/events") : "/login"}
                replace
              />
            }
          />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password/:token" element={<ResetPassword />} />
          <Route path="/join/:code" element={<JoinEvent />} />

          <Route
            path="/profile/setup"
            element={
              <RequireAuth allowIncompleteProfile>
                <ProfileSetup />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <ProfileSetup editMode />
              </RequireAuth>
            }
          />

          <Route
            path="/events"
            element={
              <RequireAuth>
                <MyEvents />
              </RequireAuth>
            }
          />
          <Route
            path="/events/:id"
            element={
              <RequireAuth>
                <EventDirectory />
              </RequireAuth>
            }
          />
          <Route
            path="/contacts"
            element={
              <RequireAuth>
                <SavedContacts />
              </RequireAuth>
            }
          />
          <Route
            path="/discover"
            element={
              <RequireAuth>
                <Discover />
              </RequireAuth>
            }
          />
          <Route
            path="/messages"
            element={
              <RequireAuth>
                <Messages />
              </RequireAuth>
            }
          />
          <Route
            path="/messages/:userId"
            element={
              <RequireAuth>
                <Messages />
              </RequireAuth>
            }
          />

          <Route
            path="/admin"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminDashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/events"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminEvents />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/events/:id"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminEventDetail />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/templates"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminTemplates />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/users"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminUsers />
              </RequireAuth>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <Footer />
    </div>
  );
}
