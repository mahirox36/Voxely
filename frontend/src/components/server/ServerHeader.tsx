import { ServerControls } from "./ServerControls";

interface ServerHeaderProps {
  name: string;
  status: string;
  type: string;
  version: string;
  isOnline: boolean;
  isStarting: boolean;
  isStopping: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onBack: () => void;
}

export const ServerHeader = ({
  name,
  status,
  type,
  version,
  isOnline,
  isStarting,
  isStopping,
  onStart,
  onStop,
  onRestart,
  onBack,
}: ServerHeaderProps) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "online":
        return "bg-green-500/20 text-green-300";
      case "starting":
        return "bg-blue-500/20 text-blue-300";
      case "stopping":
        return "bg-yellow-500/20 text-yellow-300";
      case "offline":
      default:
        return "bg-red-500/20 text-red-300";
    }
  };

  const getStatusDisplay = (status: string) => {
    // if (actionInProgress === "starting") return "Starting";
    // if (actionInProgress === "stopping") return "Stopping";
    // if (actionInProgress === "online") return "Online";
    // if (actionInProgress === "offline") return "Offline";
    // if (actionInProgress === "restarting") return "Restarting";
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <button
          onClick={onBack}
          className="text-white opacity-60 hover:opacity-100 transition-opacity"
        >
          ← Back to Dashboard
        </button>
        <h1 className="text-4xl font-bold text-white mt-2">
          {name}
          <span
            className={`ml-3 text-sm px-2 py-1 rounded ${getStatusColor(
              status
            )}`}
          >
            {getStatusDisplay(status)}
          </span>
        </h1>
        <p className="text-white/60 mt-1">
          {type.charAt(0).toUpperCase() + type.slice(1)} Server • {version}
        </p>
      </div>

      <ServerControls
        isOnline={isOnline}
        isStarting={isStarting}
        isStopping={isStopping}
        onStart={onStart}
        onStop={onStop}
        onRestart={onRestart}
      />
    </div>
  );
};
