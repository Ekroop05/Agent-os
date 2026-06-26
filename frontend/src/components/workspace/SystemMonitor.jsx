import { useEffect, useState } from "react";
import "./sprint5.css";

export default function SystemMonitor({ systemStatus }) {
  const [metrics, setMetrics] = useState({
    cpu: 0,
    ram: 0,
    disk: 0,
    uptime: "0m",
    os_mem: 0,
    py_procs: 0,
  });

  useEffect(() => {
    if (systemStatus) {
      setMetrics({
        cpu: systemStatus.cpu_usage || 0,
        ram: systemStatus.memory_usage || 0,
        disk: systemStatus.disk_usage || 0,
        uptime: systemStatus.system_uptime || "0m",
        os_mem: systemStatus.process_memory_mb || 0,
        py_procs: systemStatus.python_processes || 0,
      });
    }
  }, [systemStatus]);

  const getStatusClass = (val) => {
    if (val < 60) return "safe";
    if (val < 85) return "warn";
    return "danger";
  };

  return (
    <div className="sm-grid bc-stagger-2">
      <div className="sm-card">
        <div className="sm-header">
          <span className="sm-title">CPU Usage</span>
          <span className="sm-value">{metrics.cpu}%</span>
        </div>
        <div className="sm-meter-bg">
          <div className={`sm-meter-fill ${getStatusClass(metrics.cpu)}`} style={{ width: `${metrics.cpu}%` }}></div>
        </div>
        <div className="sm-details">
          <span>System Load</span>
          <span>{metrics.py_procs} Python Procs</span>
        </div>
      </div>

      <div className="sm-card">
        <div className="sm-header">
          <span className="sm-title">Memory Usage</span>
          <span className="sm-value">{metrics.ram}%</span>
        </div>
        <div className="sm-meter-bg">
          <div className={`sm-meter-fill ${getStatusClass(metrics.ram)}`} style={{ width: `${metrics.ram}%` }}></div>
        </div>
        <div className="sm-details">
          <span>System RAM</span>
          <span>Agent OS: {metrics.os_mem} MB</span>
        </div>
      </div>

      <div className="sm-card">
        <div className="sm-header">
          <span className="sm-title">Disk Usage</span>
          <span className="sm-value">{metrics.disk}%</span>
        </div>
        <div className="sm-meter-bg">
          <div className={`sm-meter-fill ${getStatusClass(metrics.disk)}`} style={{ width: `${metrics.disk}%` }}></div>
        </div>
        <div className="sm-details">
          <span>Root Partition</span>
          <span>Uptime: {metrics.uptime}</span>
        </div>
      </div>
    </div>
  );
}
