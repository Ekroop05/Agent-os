export default function TaskPanel({ tasks }) {
  return (
    <section className="panel fixed-panel">
      <h2>Tasks</h2>

      {tasks.map((task) => (
        <div key={task.id} className="task-row">
          <span>{task.title}</span>

          <span
            className={
              task.status === "Completed"
                ? "status-text status-completed"
                : "status-text status-pending"
            }
          >
            {task.status}
          </span>
        </div>
      ))}
    </section>
  );
}
