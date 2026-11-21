import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Layout, { GuestRoute, ProtectedRoute } from "./components/Layout";
import AuthPage from "./pages/AuthPage";
import CollectionPage from "./pages/CollectionPage";
import DeckDetailPage from "./pages/DeckDetailPage";
import DecksPage from "./pages/DecksPage";
import NotFoundPage from "./pages/NotFoundPage";
import SearchPage from "./pages/SearchPage";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route element={<GuestRoute />}>
              <Route path="/login" element={<AuthPage mode="login" />} />
              <Route path="/signup" element={<AuthPage mode="signup" />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Navigate to="/decks" replace />} />
              <Route path="/decks" element={<DecksPage />} />
              <Route path="/decks/:id" element={<DeckDetailPage />} />
              <Route path="/collection" element={<CollectionPage />} />
              <Route path="/search" element={<SearchPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
