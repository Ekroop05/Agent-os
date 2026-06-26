import { useState, useEffect, useRef } from 'react';
import './workspace-intelligence.css';

/**
 * BuildReplay — Feature 8
 * Replay mode for completed builds. Steps through tasks sorted by completed_at
 * with play/pause control and progress bar.
 */
export default function BuildReplay({ tasks, workspace }) {
  const completedTasks = tasks
    .filter((t) => t.status === 'Completed' && t.completed_at)
    .sort((a, b) => new Date(a.completed_at) - new Date(b.completed_at));

  const allTasks = tasks
    .filter((t) => t.completed_at || t.status === 'Completed')
    .sort((a, b) => {
      const aTime = a.completed_at ? new Date(a.completed_at) : new Date();
      const bTime = b.completed_at ? new Date(b.completed_at) : new Date();
      return aTime - bTime;
    });

  const replayTasks = allTasks.length > 0 ? allTasks : completedTasks;

  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (playing && step < replayTasks.length) {
      intervalRef.current = setInterval(() => {
        setStep((s) => {
          if (s >= replayTasks.length - 1) {
            setPlaying(false);
            return s;
          }
          return s + 1;
        });
      }, 1200);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, step, replayTasks.length]);

  if (replayTasks.length === 0) {
    return null; // Don't render if no tasks to replay
  }

  const progress = replayTasks.length > 0
    ? Math.round(((step + 1) / replayTasks.length) * 100)
    : 0;

  function handlePlayPause() {
    if (step >= replayTasks.length - 1) {
      setStep(0);
      setPlaying(true);
    } else {
      setPlaying(!playing);
    }
  }

  return (
    <div className="wi-section">
      <div className="wi-section-header">
        <h3 className="wi-section-title">Build Replay</h3>
        <span className="wi-section-badge">
          {step + 1} / {replayTasks.length}
        </span>
      </div>
      <div className="wi-replay">
        <div className="wi-replay-controls">
          <button
            className={`wi-replay-btn ${!playing ? 'paused' : ''}`}
            onClick={handlePlayPause}
          >
            {playing ? '⏸ Pause' : '▶ Play'}
          </button>
          <div className="wi-replay-progress">
            <div className="ui-progress-container">
              <div
                className="ui-progress-bar"
                style={{ width: `${progress}%`, transition: 'width 0.5s ease' }}
              />
            </div>
          </div>
          <span className="wi-replay-step-label">{progress}%</span>
        </div>

        <div className="wi-replay-feed">
          {replayTasks.map((task, idx) => {
            const isDone = idx < step;
            const isActive = idx === step;
            const isHidden = idx > step + 5; // Only show nearby items
            if (isHidden) return null;

            return (
              <div
                className={`wi-replay-item ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}
                key={task.id}
              >
                <div className={`wi-replay-check ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}>
                  {isDone ? '✓' : isActive ? '•' : ''}
                </div>
                <span>{task.title || 'Untitled'}</span>
                {task.output_files && task.output_files.length > 0 && isDone && (
                  <span style={{ marginLeft: 'auto', fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                    {task.output_files.length} files
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
