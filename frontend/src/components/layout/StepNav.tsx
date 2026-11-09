import React from 'react';
import { Check, Circle, CircleAlert } from 'lucide-react';
import { motion } from 'motion/react';
import { useDemo } from '../../store/demoStore';
import type { ScreenStep } from '../../types/bundlegraph';

const STEPS: Array<{ id: ScreenStep; label: string; unavailable: string }> = [
  { id: 'builder', label: 'Describe', unavailable: '' },
  { id: 'review', label: 'Confirm requirements', unavailable: 'Describe the setup first.' },
  { id: 'comparison', label: 'Compare bundles', unavailable: 'Confirm requirements and generate bundles first.' },
  { id: 'approval', label: 'Review & approve', unavailable: 'Select and save a bundle first.' },
  { id: 'execution', label: 'Track & recover', unavailable: 'No execution or recovery record is available.' },
];

export const StepNav: React.FC = () => {
  const { currentStep, setStep, canNavigate } = useDemo();
  const currentIndex = STEPS.findIndex((step) => step.id === currentStep);
  return <nav className="workflow-nav" aria-label="Bundle planning workflow"><ol>{STEPS.map((step, index) => {
    const active = currentStep === step.id;
    const available = canNavigate(step.id);
    const complete = index < currentIndex && available;
    return <li key={step.id}>
      <button type="button" className={`workflow-step ${active ? 'is-active' : ''} ${complete ? 'is-complete' : ''}`} onClick={() => setStep(step.id)} disabled={!available} aria-current={active ? 'step' : undefined} title={!available ? step.unavailable : undefined}>
        {active && <motion.span className="workflow-step__indicator" layoutId="workflow-step" aria-hidden="true" />}
        <span className="workflow-step__number" aria-hidden="true">{complete ? <Check size={14} /> : available ? <Circle size={13} /> : <CircleAlert size={13} />}</span>
        <span><small>Step {index + 1}</small>{step.label}</span>
      </button>
    </li>;
  })}</ol></nav>;
};
