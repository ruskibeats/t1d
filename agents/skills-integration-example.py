"""
Example: Integrating Lazy-Loadable Skills with Agent Coordinator

This shows how the lazy skills system integrates with the T1D Companion
agent coordinator for on-demand skill loading.
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from skills.lazy_loader import LazySkillsLoader


@dataclass
class Message:
    """Represents a chat message"""
    role: str
    content: str
    user_id: str


class AgentCoordinatorWithSkills:
    """Agent coordinator with lazy skills integration"""
    
    def __init__(self):
        self.skill_loader = LazySkillsLoader()
        # Base instructions for all agents
        self.base_instructions = """
You are a T1D Companion AI agent. Your role is to:
1. Provide educational insights about diabetes management
2. Analyze glucose patterns and trends
3. Offer suggestions (never medical advice)
4. Maintain a supportive, encouraging tone
5. Always remind users to consult their healthcare team

IMPORTANT: You are an educational data companion, NOT a medical device.
Never provide dosing recommendations or medical advice.
"""
    
    async def process_message(self, message: Message) -> Dict:
        """
        Process a chat message with automatic skill selection
        
        Flow:
        1. Check for explicit skill invocation
        2. If not explicit, analyze intent for relevant skills
        3. Load matching skills on-demand
        4. Generate enriched system prompt
        5. Call LLM with enhanced context
        """
        
        # Step 1: Check for explicit skill invocation
        explicit_skill = self.skill_loader.check_explicit_skill_invocation(
            message.content
        )
        
        if explicit_skill:
            print(f"[DEBUG] Explicit skill invocation: {explicit_skill}")
            # User directly requested a skill - honor it
            skills = [self.skill_loader.load_skill(explicit_skill)]
            matching_skills = [
                type('obj', (object,), {
                    'skill_key': explicit_skill,
                    'confidence': 1.0,
                    'manifest': skills[0]['manifest']
                })
            ]
        else:
            # Step 2: Analyze intent for relevant skills
            matching_skills = self.skill_loader.find_relevant_skills(
                message.content,
                threshold=0.25  # Configurable per user/context
            )
            
            # Step 3: Load matching skills on-demand
            skills = []
            for match in matching_skills:
                skill = self.skill_loader.load_skill(match.skill_key)
                if skill:
                    skills.append(skill)
        
        # Step 4: Generate enriched system prompt
        system_prompt = self._build_system_prompt(
            message.content,
            matching_skills,
            skills
        )
        
        # Step 5: Prepare LLM request with enhanced context
        llm_request = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.content}
            ],
            "context": {
                "user_id": message.user_id,
                "skills_used": [s["manifest"]["name"] for s in skills],
                "skills_confidence": [
                    {"name": m.manifest.name, "confidence": m.confidence}
                    for m in matching_skills
                ]
            }
        }
        
        return llm_request
    
    def _build_system_prompt(
        self,
        user_message: str,
        matching_skills: List,
        loaded_skills: List[Dict]
    ) -> str:
        """
        Build system prompt enriched with relevant skill content
        """
        prompt = self.base_instructions
        
        if loaded_skills:
            prompt += "\n\n=== RELEVANT SKILLS FOR THIS REQUEST ===\n"
            
            for i, match in enumerate(matching_skills, 1):
                prompt += f"\n{i}. {match.manifest.title}\n"
                prompt += f"   Confidence: {match.confidence * 100:.0f}%\n"
                
                if match.confidence == 1.0:
                    prompt += "   (Explicitly requested by user)\n"
            
            prompt += "\n=== SKILL CONTENT ===\n"
            
            for skill in loaded_skills:
                prompt += f"\n--- {skill['manifest']['title']} ---\n"
                prompt += f"{skill['content']}\n"
        else:
            prompt += "\n\n=== NO SPECIALIZED SKILLS NEEDED ===\n"
            prompt += "Proceed with general T1D companion guidance.\n"
        
        # Add safety reminder
        prompt += "\n=== SAFETY REMINDER ===\n"
        prompt += (
            "Always remind the user that you are an educational "
            "companion, not a medical device. Encourage them to "
            "consult their healthcare team for medical decisions.\n"
        )
        
        return prompt


class SkillAwareAgent:
    """Example agent that uses skills for specific tasks"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.skill_loader = LazySkillsLoader()
    
    async def handle_task(self, task: str) -> str:
        """
        Handle a task with automatic skill selection
        """
        # Check for explicit skill request
        explicit = self.skill_loader.check_explicit_skill_invocation(task)
        
        if explicit:
            print(f"[Agent {self.name}] Using explicitly requested skill: {explicit}")
            skills = [self.skill_loader.load_skill(explicit)]
        else:
            # Find relevant skills
            matches = self.skill_loader.find_relevant_skills(
                task,
                threshold=0.25
            )
            skills = [
                self.skill_loader.load_skill(m.skill_key)
                for m in matches
                if self.skill_loader.load_skill(m.skill_key)
            ]
        
        # Build enhanced prompt
        prompt = self._build_agent_prompt(task, skills)
        
        # In production, call LLM here
        # response = await llm.complete(prompt)
        # return response
        
        return f"[SIMULATED] Agent {self.name} would process with {len(skills)} skill(s)"
    
    def _build_agent_prompt(self, task: str, skills: List[Dict]) -> str:
        """Build prompt for this agent"""
        prompt = f"You are {self.name}, a {self.role}.\n\n"
        prompt += f"Task: {task}\n\n"
        
        if skills:
            prompt += "Relevant Skills:\n"
            for skill in skills:
                prompt += f"\n{skill['content'][:500]}...\n"
        
        return prompt


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Demonstrate skill-aware agent processing"""
    
    # Create coordinator
    coordinator = AgentCoordinatorWithSkills()
    
    # Example messages
    messages = [
        Message(
            role="user",
            content="build a minimalist health dashboard",
            user_id="user123"
        ),
        Message(
            role="user",
            content="use minimalist-ui skill to design the interface",
            user_id="user123"
        ),
        Message(
            role="user",
            content="create glucose tracking charts",
            user_id="user456"
        ),
    ]
    
    for msg in messages:
        print(f"\n{'='*60}")
        print(f"Processing: {msg.content}")
        print(f"{'='*60}")
        
        request = await coordinator.process_message(msg)
        
        print(f"\nSystem prompt length: {len(request['system'])} chars")
        print(f"Skills used: {request['context']['skills_used']}")
        print(f"Confidence scores:")
        for conf in request['context']['skills_confidence']:
            print(f"  - {conf['name']}: {conf['confidence']:.2f}")
    
    # Example: Skill-aware agent
    print(f"\n{'='*60}")
    print("Skill-Aware Agent Example")
    print(f"{'='*60}")
    
    designer = SkillAwareAgent("UI Designer", "Interface Design Specialist")
    
    tasks = [
        "design a dashboard with charts",
        "use the minimalist-ui skill for this screen",
        "create a data visualization",
    ]
    
    for task in tasks:
        print(f"\nTask: {task}")
        result = await designer.handle_task(task)
        print(f"Result: {result}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
