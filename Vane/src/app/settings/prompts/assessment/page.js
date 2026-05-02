'use client'

import PromptManager from '@/components/PromptManager'

export default function AssessmentPromptsPage() {
    return (
        <PromptManager
            group="assessment"
            titleKey="prompts.assessmentTitle"
            descKey="prompts.assessmentDesc"
        />
    )
}
