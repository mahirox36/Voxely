import React, { createContext, useContext, useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";

type ModalType = "info" | "confirm" | "input" | "custom";

type ModalOptions = {
  type: ModalType;
  title?: string;
  content?: React.ReactNode | string;
  confirmText?: string;
  cancelText?: string;
  placeholder?: string;
  defaultValue?: string;
  // for custom modals you can provide a render function/component
  custom?: React.ReactNode;
};

type ModalInstance = {
  id: string;
  options: ModalOptions;
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
};

type ModalContextValue = {
  showModal: (opts: ModalOptions) => Promise<unknown>;
  hideModal: (id?: string, value?: unknown) => void;
};

const ModalContext = createContext<ModalContextValue | null>(null);

export const useModal = () => {
  const ctx = useContext(ModalContext);
  if (!ctx) {
    throw new Error("useModal must be used within a ModalProvider");
  }
  return ctx;
};

export const ModalProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [modals, setModals] = useState<ModalInstance[]>([]);

  const showModal = useCallback((options: ModalOptions) => {
    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    return new Promise<unknown>((resolve, reject) => {
      const instance: ModalInstance = { id, options, resolve, reject };
      setModals((m) => [...m, instance]);
    });
  }, []);

  const hideModal = useCallback((id?: string, value?: unknown) => {
    setModals((current) => {
      if (!id) {
        // close top-most
        const last = current[current.length - 1];
        if (last) last.resolve(value);
        return current.slice(0, -1);
      }
      const idx = current.findIndex((m) => m.id === id);
      if (idx === -1) return current;
      const inst = current[idx];
      if (inst) inst.resolve(value);
      return [...current.slice(0, idx), ...current.slice(idx + 1)];
    });
  }, []);

  const contextValue: ModalContextValue = {
    showModal,
    hideModal,
  };

  return (
    <ModalContext.Provider value={contextValue}>
      {children}
      <AnimatePresence>
        {modals.map((modal) => (
          <ModalRenderer
            key={modal.id}
            instance={modal}
            onClose={(value?: unknown) => hideModal(modal.id, value)}
          />
        ))}
      </AnimatePresence>
    </ModalContext.Provider>
  );
};

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const panelVariants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

const ModalRenderer: React.FC<{
  instance: ModalInstance;
  onClose: (value?: unknown) => void;
}> = ({ instance, onClose }) => {
  const { options } = instance;
  const [inputValue, setInputValue] = useState(
    options.defaultValue ?? ""
  );

  const renderContent = () => {
    switch (options.type) {
      case "info":
        return (
          <>
            <div className="mb-4 text-sm text-white/80">
              {options.content}
            </div>
            <div className="flex justify-center">
              <button
                className="btn btn-primary"
                onClick={() => onClose(true)}
              >
                {options.confirmText || "OK"}
              </button>
            </div>
          </>
        );
      case "confirm":
        return (
          <>
            <div className="mb-6 text-sm text-white/80">
              {options.content}
            </div>
            <div className="flex justify-center gap-4">
              <button
                className="btn btn-secondary"
                onClick={() => onClose(false)}
              >
                {options.cancelText || "Cancel"}
              </button>
              <button
                className="btn btn-primary"
                onClick={() => onClose(true)}
              >
                {options.confirmText || "Accept"}
              </button>
            </div>
          </>
        );
      case "input":
        return (
          <>
            <div className="mb-4 text-sm text-white/80">
              {options.content}
            </div>
            <input
              autoFocus
              className="w-full p-2 rounded bg-white/5 mb-4 text-white"
              placeholder={options.placeholder || ""}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <div className="flex justify-center gap-4">
              <button
                className="btn btn-secondary"
                onClick={() => onClose(null)}
              >
                {options.cancelText || "Cancel"}
              </button>
              <button
                className="btn btn-primary"
                onClick={() => onClose(inputValue)}
              >
                {options.confirmText || "Submit"}
              </button>
            </div>
          </>
        );
      case "custom":
        return options.custom ?? null;
      default:
        return null;
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial="hidden"
      animate="visible"
      exit="hidden"
      variants={overlayVariants}
    >
      <motion.div
        className="absolute inset-0 bg-black/70"
        onClick={() => onClose(false)}
        aria-hidden
      />
      <motion.div
        className="glass-card w-full max-w-2xl z-50 p-6"
        variants={panelVariants}
        initial="hidden"
        animate="visible"
        exit="hidden"
      >
        {options.title && (
          <h3 className="text-xl font-bold text-white mb-3">
            {options.title}
          </h3>
        )}
        {renderContent()}
      </motion.div>
    </motion.div>
  );
};

export default ModalProvider;
