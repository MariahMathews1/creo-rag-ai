from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Advisory AI interface. Implementations cannot alter deterministic findings."""

    @abstractmethod
    def explain_gcode(self, text: str) -> str: ...

    @abstractmethod
    def explain_cl_data(self, text: str) -> str: ...

    @abstractmethod
    def summarize_findings(self, text: str) -> str: ...

    @abstractmethod
    def compare_cl_to_gcode(self, cl_text: str, gcode_text: str) -> str: ...

    @abstractmethod
    def answer_manual_question(self, manual_text: str, question: str) -> str: ...


class MockAIProvider(AIProvider):
    """Offline placeholder used until an approved provider is configured."""

    prefix = "Advisory mock response — no external AI call was made."

    def explain_gcode(self, text: str) -> str:
        lines = len([line for line in text.splitlines() if line.strip()])
        return f"{self.prefix} The submitted G-code contains {lines} nonblank lines. Review the deterministic findings and simulate the complete program."

    def explain_cl_data(self, text: str) -> str:
        return f"{self.prefix} CL/NCL content was received for plain-language review. Verify all operations against the Creo setup and machine configuration."

    def summarize_findings(self, text: str) -> str:
        return f"{self.prefix} Findings require qualified programmer review. Blocking results should be resolved before warnings and informational observations."

    def compare_cl_to_gcode(self, cl_text: str, gcode_text: str) -> str:
        return f"{self.prefix} Automated CL-to-G-code comparison is not enabled in the local provider."

    def answer_manual_question(self, manual_text: str, question: str) -> str:
        return f"{self.prefix} Manual question answering is not enabled in the local provider."

