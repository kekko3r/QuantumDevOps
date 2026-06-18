"""
Quantum DevOps Mining — Query Definitions
Fonte fasi: Gheorghe-Pop et al. (IEEE 2020)
Fonte terminologia ibrida/servizi: Moguel et al. (arXiv 2309.11926)
"""

# Blocco CONTESTO — comune a tutte le query
CONTEXT_TERMS = [
    "quantum", "qiskit", "pennylane", "cirq", "braket",
    "cuda-q", "azure quantum", "quantum service",
    "QCaaS", "QaaS", "hybrid", "classical-quantum",
    "quantum-classical", "hybrid workflow",
    "classical-quantum integration",
    "quantum-classical communication"
]

# Blocchi FASE — ognuno in AND con il CONTESTO
PHASE_QUERIES = {
    "PLAN": [
        "algorithm design", "circuit design", "ansatz",
        "requirements", "problem encoding"
    ],
    "CODE": [
        "implement", "OpenQASM", "hybrid code",
        "hybrid loop", "variational", "programming"
    ],
    "BUILD": [
        "transpile", "transpilation", "compilation",
        "gate mapping", "qubit mapping", "optimization level",
        "quilc", "quil", "nvq++"
    ],
    "TEST": [
        "simulate", "simulation", "noise model", "test",
        "shot noise", "error mitigation", "real hardware",
        "QVM", "simulator"
    ],
    "RELEASE": [
        "version", "deprecated", "breaking change",
        "migration", "package", "changelog"
    ],
    "EVALUATE": [
        "backend selection", "which backend", "calibration",
        "reliable", "reliability", "quantum volume", "error rate",
        "resource estimator"
    ],
    "DEPLOY_CONFIGURE": [
        "deploy", "deployment", "job submission", "submit",
        "configure", "configuration", "credentials",
        "container", "orchestrate", "orchestration",
        "OpenAPI", "quantum API", "hybrid jobs",
        "session", "primitive", "Sampler", "Estimator"
    ],
    "MONITOR": [
        "queue", "job status", "monitor", "monitoring",
        "execution time", "results retrieval", "hybrid execution"
    ],
    "FEEDBACK": [
        "results distribution", "interpret results",
        "counts", "histogram", "result quality",
        "optimization rate"
    ],
    "CROSS_CICD": [
        "CI/CD", "continuous integration",
        "continuous deployment", "pipeline",
        "GitHub Actions", "quantum devops", "workflow",
        "orchestrate", "data exchange", "service",
        "microservice", "distributed"
    ]
}
