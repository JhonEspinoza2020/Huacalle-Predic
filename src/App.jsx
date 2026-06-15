import { useEffect, useState } from "react";
import AdminApp from "./AdminApp";
import DocenteApp from "./DocenteApp";
import LoginScreen from "./LoginScreen";
import {
  API_BASE,
  authFetchJson,
  clearSession,
  getStoredToken,
  getStoredUser,
} from "./apiClient";

function App() {
  const [authUser, setAuthUser] = useState(() => getStoredUser());
  const [authReady, setAuthReady] = useState(!getStoredToken());

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setAuthReady(true);
      return;
    }
    authFetchJson(`${API_BASE}/api/auth/me`)
      .then((data) => setAuthUser(data.user))
      .catch(() => {
        clearSession();
        setAuthUser(null);
      })
      .finally(() => setAuthReady(true));
  }, []);

  const handleLogout = () => {
    clearSession();
    setAuthUser(null);
  };

  if (!authReady) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-400">
        Verificando sesion...
      </main>
    );
  }

  if (!authUser) {
    return <LoginScreen onLoggedIn={setAuthUser} />;
  }

  if (authUser.rol === "admin") {
    return <AdminApp user={authUser} onLogout={handleLogout} />;
  }

  return <DocenteApp user={authUser} onLogout={handleLogout} />;
}

export default App;
