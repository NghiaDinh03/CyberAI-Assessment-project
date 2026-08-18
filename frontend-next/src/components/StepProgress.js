'use client';
import { CheckCircle2, Circle } from 'lucide-react';
import styles from './StepProgress.module.css';

const STEPS = ['Organization', 'Infrastructure', 'Controls', 'Review'];

export default function StepProgress({ currentStep }) {
  return (
    <div className={styles.wrapper}>
      {STEPS.map((label, i) => {
        const idx = i + 1;
        const done = idx < currentStep;
        const active = idx === currentStep;
        return (
          <div key={label} className={`${styles.step} ${done ? styles.done : ''} ${active ? styles.active : ''}`}>
            <div className={styles.icon}>
              {done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
            </div>
            <span className={styles.label}>{label}</span>
            {i < STEPS.length - 1 && <div className={styles.connector} />}
          </div>
        );
      })}
    </div>
  );
}
