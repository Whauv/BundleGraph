import React from 'react';
import { useDemo } from '../../store/demoStore';
import type { ScreenStep } from '../../types/bundlegraph';
import { Terminal, CheckSquare, GitCompare, Lock, Activity, Check } from 'lucide-react';

interface StepItem {
  id: ScreenStep;
  label: string;
  number: number;
  icon: React.ComponentType<{ size?: number; style?: React.CSSProperties; className?: string }>;
}

const STEPS: StepItem[] = [
  { id: 'builder', label: '1. Request Builder', number: 1, icon: Terminal },
  { id: 'review', label: '2. Requirements Review', number: 2, icon: CheckSquare },
  { id: 'comparison', label: '3. Comparison & Graph', number: 3, icon: GitCompare },
  { id: 'approval', label: '4. Plan Authorization', number: 4, icon: Lock },
  { id: 'execution', label: '5. Execution & Recovery', number: 5, icon: Activity },
];

const STEP_ORDER: ScreenStep[] = ['builder', 'review', 'comparison', 'approval', 'execution'];

export const StepNav: React.FC = () => {
  const { currentStep, setStep } = useDemo();
  const currentIndex = STEP_ORDER.indexOf(currentStep);

  return (
    <div className="step-nav-bar">
      <nav className="step-nav" aria-label="Demo workflow navigation">
        {STEPS.map((step, idx) => {
          const isActive = currentStep === step.id;
          const isCompleted = idx < currentIndex;
          const IconComponent = step.icon;

          return (
            <button
              key={step.id}
              type="button"
              className={`step-tab ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
              onClick={() => setStep(step.id)}
              aria-current={isActive ? 'step' : undefined}
              title={`Switch to ${step.label}`}
            >
              <span className="step-number">
                {isCompleted ? <Check size={12} strokeWidth={3} /> : step.number}
              </span>
              <IconComponent size={15} style={{ opacity: isActive ? 1 : 0.7 }} />
              <span>{step.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
