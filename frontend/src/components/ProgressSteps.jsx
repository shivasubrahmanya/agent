import React from 'react';
import { Check, Loader2, Circle } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const stages = [
    { id: 'discovery', label: 'Discovery' },
    { id: 'structure', label: 'Structure' },
    { id: 'roles', label: 'Role Search' },
    { id: 'enrichment', label: 'Enrichment' },
    { id: 'verification', label: 'Verification' },
];

export function ProgressSteps({ currentStage, completedStages = [] }) {
    return (
        <div className="w-full py-6">
            <div className="flex items-center justify-between relative">
                <div className="absolute left-0 top-1/2 w-full h-0.5 bg-secondary -z-10" />

                {stages.map((stage, index) => {
                    const isCompleted = completedStages.includes(stage.id);
                    const isCurrent = currentStage === stage.id;
                    const isPending = !isCompleted && !isCurrent;

                    return (
                        <div key={stage.id} className="flex flex-col items-center gap-2 bg-background px-2">
                            <div
                                className={twMerge(
                                    "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all",
                                    isCompleted ? "bg-primary border-primary text-primary-foreground" :
                                        isCurrent ? "bg-background border-primary text-primary animate-pulse" :
                                            "bg-muted border-muted-foreground/30 text-muted-foreground"
                                )}
                            >
                                {isCompleted ? <Check size={20} /> :
                                    isCurrent ? <Loader2 size={20} className="animate-spin" /> :
                                        <Circle size={20} />}
                            </div>
                            <span className={clsx("text-xs font-medium", isCurrent ? "text-primary" : "text-muted-foreground")}>
                                {stage.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
