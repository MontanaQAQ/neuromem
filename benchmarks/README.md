# NeuroMem Benchmarks

This directory contains comprehensive benchmarking tools for evaluating NeuroMem (sage.neuromem) performance.

> **Note**: This benchmark suite was migrated from the `sage-benchmark` repository to simplify development and maintenance. Having benchmarks co-located with the code ensures version synchronization and easier testing.

## Directory Structure

```
benchmarks/
├── experiment/           # Benchmark experiments and pipelines
│   ├── memory_test_pipeline.py  # Main benchmark pipeline
│   ├── config/          # Experiment configurations
│   ├── libs/            # Core benchmark libraries
│   ├── script/          # Execution scripts
│   ├── tools/           # Helper tools
│   └── utils/           # Utility functions
└── evaluation/          # Analysis and evaluation tools
    └── specialized_analysis/  # Specialized analyzers
```

## Quick Start

### Running Benchmarks

```bash
# Install benchmark dependencies
pip install -e ".[dev]"

# Run basic benchmark
python benchmarks/experiment/memory_test_pipeline.py --config benchmarks/experiment/config/default.yaml

# Run with custom config
python benchmarks/experiment/memory_test_pipeline.py --config your_config.yaml
```

### Configuration

Benchmark configurations are stored in `benchmarks/experiment/config/`. Each configuration defines:
- Memory backend settings (VDB, KV, Graph)
- Test datasets and parameters
- Evaluation metrics
- Output settings

## Components

### Experiment Pipeline

The main benchmark pipeline (`memory_test_pipeline.py`) includes:
- **MemorySource**: Data generation and loading
- **PreInsert**: Data preprocessing before insertion
- **MemoryInsert**: Memory insertion operations
- **PostInsert**: Post-insertion processing
- **PreRetrieval**: Query preprocessing
- **MemoryRetrieval**: Memory retrieval operations
- **PostRetrieval**: Results post-processing
- **MemorySink**: Results collection and storage
- **MemoryEvaluation**: Performance evaluation

### Evaluation Tools

Located in `benchmarks/evaluation/`, these tools provide:
- Performance metrics analysis
- Comparison across different configurations
- Visualization of results
- Statistical analysis

## Metrics

Benchmarks measure:
- **Insertion Performance**: Throughput, latency
- **Retrieval Performance**: Query latency, recall@k, precision
- **Memory Usage**: RAM, disk storage
- **Scalability**: Performance vs. data size
- **Index Performance**: Build time, query time

## Documentation

For more detailed documentation, see:
- [Experiment Design](../docs/benchmarks/experiment_design/)
- [Original README](README_original.md) - From sage-benchmark repository

## Migration Notes

**Migration Date**: 2026-01-05  
**From**: `sage-benchmark/src/sage/benchmark/benchmark_memory`  
**To**: `neuromem/benchmarks`

**Import Path Changes**:
- Old: `from sage.benchmark.benchmark_memory.* import ...`
- New: `from benchmarks.* import ...`

**NeuroMem Import Path**:
- Old: `from sage.middleware.components.sage_mem.neuromem import ...`
- New: `from sage.neuromem import ...`

## Contributing

When adding new benchmarks:
1. Follow the existing pipeline structure
2. Add configuration examples
3. Document metrics and expected results
4. Update this README with new benchmark descriptions

## Related

- Main NeuroMem documentation: [../README.md](../README.md)
- NeuroMem services: [../sage/neuromem/services/](../sage/neuromem/services/)
- Performance tests: [../tests/performance/](../tests/performance/)
