import { useEffect, useState } from 'react';
import Dashboard from './pages/Dashboard';
import NetworkTwin from './pages/NetworkTwin';

export default function App() {
  const [route, setRoute] = useState(window.location.hash);

  useEffect(() => {
    const updateRoute = () => setRoute(window.location.hash);
    window.addEventListener('hashchange', updateRoute);
    return () => window.removeEventListener('hashchange', updateRoute);
  }, []);

  return route === '#network-twin' ? <NetworkTwin /> : <Dashboard />;
}
