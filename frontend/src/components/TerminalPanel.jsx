export default function TerminalPanel({ logs }) {
  return (
    <section className="terminal-panel">
      <h2>Terminal</h2>

      {logs.map((log, index) => (
        <div key={index} className="terminal-line">
          {log}
        </div>
      ))}
    </section>
  );
}
