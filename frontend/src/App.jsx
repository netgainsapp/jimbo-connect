import { Routes, Route, Navigate } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import ProfileSetup from "./pages/ProfileSetup.jsx";
import MyEvents from "./pages/MyEvents.jsx";
import EventDirectory from "./pages/EventDirectory.jsx";
import SavedContacts from "./pages/SavedContacts.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import AdminEvents from "./pages/AdminEvents.jsx";
import AdminEventDetail from "./pages/AdminEventDetail.jsx";
import JoinEvent from "./pages/JoinEvent.jsx";
import { useAuth } from "./hooks/useAuth.jsx";

export default function App() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <div className="pt-14">
        <Routes>
          <Route path="/" element={<Navigate to={user ? "/events" : "/login"} replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
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

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}
