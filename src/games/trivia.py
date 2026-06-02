import asyncio
from typing import Optional
from src.ai.jarvis_brain import generate_game_question
from src.memory.database import update_game_score, get_game_leaderboard

active_trivia: Optional[dict] = None
trivia_lock = asyncio.Lock()


async def start_trivia(category: str = "geral") -> str:
    global active_trivia
    async with trivia_lock:
        if active_trivia:
            return "Já tem uma pergunta ativa! Use !resposta <resposta>"

        question_data = await generate_game_question(category)
        active_trivia = {
            "question": question_data["question"],
            "answer": question_data["answer"].lower().strip(),
            "hint": question_data.get("hint", ""),
            "difficulty": question_data.get("difficulty", "médio"),
            "attempts": 0,
        }

        return (
            f"🎮 TRIVIA [{active_trivia['difficulty'].upper()}]: {active_trivia['question']} "
            f"| Use !resposta <sua resposta>"
        )


async def check_answer(username: str, answer: str) -> Optional[str]:
    global active_trivia
    async with trivia_lock:
        if not active_trivia:
            return None

        active_trivia["attempts"] += 1
        user_answer = answer.lower().strip()
        correct = active_trivia["answer"]

        # Flexible matching
        if user_answer == correct or correct in user_answer or user_answer in correct:
            question = active_trivia["question"]
            active_trivia = None
            await update_game_score(username, "trivia", score_delta=10, win=True)
            return f"🏆 @{username} acertou! A resposta era: {correct} | +10 pontos!"

        if active_trivia["attempts"] >= 3 and active_trivia["hint"]:
            return f"Dica: {active_trivia['hint']}"

        if active_trivia["attempts"] >= 5:
            answer_text = active_trivia["answer"]
            active_trivia = None
            return f"Ninguém acertou! A resposta era: {answer_text}"

        return f"@{username} Resposta errada! Tente novamente."


async def skip_trivia() -> str:
    global active_trivia
    async with trivia_lock:
        if not active_trivia:
            return "Não há trivia ativa no momento."
        answer = active_trivia["answer"]
        active_trivia = None
        return f"Trivia cancelada. A resposta era: {answer}"


async def get_trivia_leaderboard() -> str:
    leaders = await get_game_leaderboard("trivia", 5)
    if not leaders:
        return "Nenhuma pontuação ainda! Use !trivia para começar."
    lines = ["🏆 TOP TRIVIA:"]
    for i, l in enumerate(leaders, 1):
        lines.append(f"{i}. {l['username']} - {l['score']}pts ({l['wins']} vitórias)")
    return " | ".join(lines)
