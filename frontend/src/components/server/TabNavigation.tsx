interface TabNavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const TabNavigation = ({ activeTab, onTabChange }: TabNavigationProps) => {
  const tabs = [
    'overview',
    'console',
    'files',
    'players',
    'config',
    'plugins/Mods',
    'backups',
    'logs',
    'settings'
  ];

  return (
    <div className="flex space-x-2 mt-6 border-b border-white/10">
      {tabs.map((tab) => (
        <button
          key={tab}
          onClick={() => onTabChange(tab)}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors
            ${activeTab === tab 
              ? 'bg-white/10 text-white border-b-2 border-pink-500' 
              : 'text-white/60 hover:text-white hover:bg-white/5'}`}
        >
          {tab.charAt(0).toUpperCase() + tab.slice(1)}
        </button>
      ))}
    </div>
  );
};