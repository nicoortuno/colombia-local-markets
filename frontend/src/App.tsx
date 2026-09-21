import { useHealth } from "./hooks/useHealth";

function App() {
  const { data, isLoading, isError } = useHealth();

  return (
    <main>
      <h1>Colombia Local Markets</h1>

      {isLoading && <p>Connecting to API...</p>}

      {isError && <p>Backend connection failed.</p>}

      {data && (
        <>
          <p>API: {data.status}</p>
          <p>PostgreSQL: {data.database}</p>
        </>
      )}
    </main>
  );
}

export default App;
