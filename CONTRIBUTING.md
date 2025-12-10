# Contributing to HP Paperless Sync

Thank you for your interest in contributing to HP Paperless Sync! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/hp-paperless-sync.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment:
   - Linux/Mac: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
5. Install dependencies: `pip install -r requirements.txt`

## Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Keep functions focused and single-purpose
- Add docstrings to all public functions and classes

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in imperative mood (e.g., "Fix upload retry logic")
- Reference issue numbers when applicable (e.g., "Fix #123: Handle network errors")

### Pull Request Process

1. Create a feature branch from `main`: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Test your changes thoroughly
4. Update documentation if needed
5. Submit a pull request with a clear description of changes

## Testing

Before submitting a PR, please ensure:
- The application runs without errors
- Configuration validation works correctly
- File upload functionality is tested (if applicable)
- Error handling is tested

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output (with sensitive information redacted)

## Feature Requests

Feature requests are welcome! Please open an issue with:
- A clear description of the feature
- Use case and motivation
- Any implementation ideas (optional)

## Questions?

Feel free to open an issue for questions or discussions about the project.

