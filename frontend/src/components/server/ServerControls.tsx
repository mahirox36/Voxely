import { Play, Square, RotateCcw } from "lucide-react";

interface ServerControlsProps {
  isOnline: boolean;
  isStarting: boolean;
  isStopping: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
}

export const ServerControls = ({
  isOnline,
  isStarting,
  isStopping,
  onStart,
  onStop,
  onRestart,
}: ServerControlsProps) => {
  return (
    <div className="flex gap-3">
      <button
        onClick={onStart}
        disabled={isOnline || isStarting || isStopping}
        className={`btn ${isOnline ? "btn-disabled" : "btn-success"}`}
      >
        <Play className="mr-2" />
        {isStarting ? "Starting..." : "Start"}
      </button>

      <button
        onClick={onStop}
        disabled={!isOnline || isStopping}
        className={`btn ${!isOnline ? "btn-disabled" : "btn-danger"}`}
      >
        <Square className="mr-2" />
        {isStopping ? "Stopping..." : "Stop"}
      </button>

      <button
        onClick={onRestart}
        disabled={!isOnline || isStarting || isStopping}
        className={`btn ${!isOnline ? "btn-disabled" : "btn-warning"}`}
      >
        <RotateCcw className="mr-2" />
        Restart
      </button>
    </div>
  );
};
