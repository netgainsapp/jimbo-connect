import { Routes, Route, Navigate, useLocation } from "react-router-dom";
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
import CrossEventDirectory from "./pages/CrossEventDirectory.jsx";
import SavedContacts from "./pages/SavedContacts.jsx";
import Discover from "./pages/Discover.jsx";
import Messages from "./pages/Messages.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import AdminEvents from "./pages/AdminEvents.jsx";
import AdminEventDetail from "./pages/AdminEventDetail.jsx";
import AdminTemplates from "./pages/AdminTemplates.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";
import AdminBlog from "./pages/AdminBlog.jsx";
import AdminNews from "./pages/AdminNews.jsx";
import AdminSalesTemplates from "./pages/AdminSalesTemplates.jsx";
import AdminAnalytics from "./pages/AdminAnalytics.jsx";
import AdminSuppressions from "./pages/AdminSuppressions.jsx";
import AdminOutreach from "./pages/AdminOutreach.jsx";
import JoinEvent from "./pages/JoinEvent.jsx";
import AgendaLandingRedirect from "./pages/AgendaLandingRedirect.jsx";
import AgendaBuilder from "./pages/AgendaBuilder.jsx";
import AgendaConvert from "./pages/AgendaConvert.jsx";
import MarketingNav from "./components/marketing/MarketingNav.jsx";
import MarketingFooter from "./components/marketing/MarketingFooter.jsx";
import Upgrade from "./pages/Upgrade.jsx";
import { useAuth } from "./hooks/useAuth.jsx";

export default function App() {
  const { user, loading } = useAuth();
  const { pathname } = useLocation();

  // Public pages that belong to the marketing surface rather than the product.
  // The Agenda Builder is a free tool linked from intro-connect.com, so it
  // wears the marketing chrome and a visitor sees one continuous site. The
  // app's own nav, and the Front Range Dev Co credit in its footer, stay on
  // authenticated product surfaces.
  const marketingSurface =
    pathname === "/agenda" || pathname.startsWith("/agenda/");

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {marketingSurface ? <MarketingNav /> : <Nav />}
      {/* The app nav is `fixed`, so content needs matching top padding. The
          marketing nav is `sticky` and occupies its own space, so padding
          there would leave a visible gap under the header. */}
      <main className={`${marketingSurface ? "" : "pt-14"} flex-1`}>
        <Routes>
          <Route
            path="/"
            element={
              // Wait for the session check before deciding where "/" goes.
              // Redirecting on `user` alone bounces a logged-in visitor to
              // /login during the initial /api/auth/me round-trip, since user
              // is still null until it resolves.
              loading ? (
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-text-muted">Loading…</div>
                </div>
              ) : (
                <Navigate
                  to={user ? (user.is_admin ? "/admin" : "/events") : "/login"}
                  replace
                />
              )
            }
          />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password/:token" element={<ResetPassword />} />
          <Route path="/join/:code" element={<JoinEvent />} />

          {/* Public by design: the Agenda Builder is a free acquisition tool,
              so it must work before the visitor has an account. Deliberately
              outside RequireAuth, alongside /join/:code. */}
          <Route path="/agenda" element={<AgendaLandingRedirect />} />
          <Route path="/agenda/new" element={<AgendaBuilder />} />
          {/* allowIncompleteProfile on purpose: the organizer sees their event
              first and is prompted for a profile afterwards, so profile setup
              must not stand between them and the thing they came for. */}
          <Route
            path="/agenda/convert"
            element={
              <RequireAuth allowIncompleteProfile>
                <AgendaConvert />
              </RequireAuth>
            }
          />

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
            path="/upgrade"
            element={
              // Incomplete profiles may still pick a plan; paying should never
              // be blocked behind profile setup.
              <RequireAuth allowIncompleteProfile>
                <Upgrade />
              </RequireAuth>
            }
          />
          <Route
            path="/directory"
            element={
              <RequireAuth>
                <CrossEventDirectory />
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
          <Route
            path="/admin/blog"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminBlog />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/news"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminNews />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/analytics"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminAnalytics />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/suppressions"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminSuppressions />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/sales-templates"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminSalesTemplates />
              </RequireAuth>
            }
          />
          <Route
            path="/admin/outreach"
            element={
              <RequireAuth adminOnly allowIncompleteProfile>
                <AdminOutreach />
              </RequireAuth>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {marketingSurface ? <MarketingFooter /> : <Footer />}
    </div>
  );
}
