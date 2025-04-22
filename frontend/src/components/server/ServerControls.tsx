import { FaPlay, FaStop, FaRedo } from "react-icons/fa";

interface ServerControlsProps {
  isOnline: boolean;
  isStarting: boolean;
  isStopping: boolean;
  isRestarting: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
}

export const ServerControls = ({
  isOnline,
  isStarting,
  isStopping,
  isRestarting,
  onStart,
  onStop,
  onRestart,
}: ServerControlsProps) => {
  return (
    <div className="flex gap-3">
      <button
        onClick={onStart}
        disabled={isOnline || isStarting || isStopping || isRestarting}
        className={`btn ${isOnline ? "btn-disabled" : "btn-success"}`}
      >
        <FaPlay className="mr-2" />
        {isStarting ? "Starting..." : "Start"}
      </button>

      <button
        onClick={onStop}
        disabled={!isOnline || isStopping || isRestarting}
        className={`btn ${!isOnline ? "btn-disabled" : "btn-danger"}`}
      >
        <FaStop className="mr-2" />
        {isStopping ? "Stopping..." : "Stop"}
      </button>

      <button
        onClick={onRestart}
        disabled={!isOnline || isStarting || isStopping || isRestarting}
        className={`btn ${!isOnline ? "btn-disabled" : "btn-warning"}`}
      >
        <FaRedo className="mr-2" />
        {isRestarting ? "Restarting..." : "Restart"}
      </button>
    </div>
  );
};