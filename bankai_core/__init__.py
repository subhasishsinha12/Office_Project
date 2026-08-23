"""BankAI Core — bank-owned AI platform layer.

Applications (BranchOne, and future CreditOne/RMOne/etc.) must never import
a model provider or the CBS adapter directly. All AI access goes through
`bankai_core.gateway.ai_gateway.AIGateway`; all core-banking access goes
through `bankai_core.tools.gateway.ToolGateway`.
"""
