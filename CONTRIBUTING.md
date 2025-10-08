# Contributing to BuddyCtl

Thank you for your interest in contributing to BuddyCtl! 🎉

## How to Contribute

### Reporting Bugs 🐛

If you find a bug, please create an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Poetry version)

### Suggesting Features 💡

We welcome feature suggestions! Please:
- Check if the feature was already suggested
- Explain the use case and benefits
- Provide examples if possible

### Code Contributions 🔧

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/buddyctl.git
   cd buddyctl
   ```

2. **Set up development environment**
   ```bash
   poetry install
   poetry run buddyctl --help
   ```

3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make your changes**
   - Write clean, readable code
   - Follow existing code style
   - Add tests for new features
   - Update documentation if needed

5. **Run tests and linters**
   ```bash
   poetry run pytest
   poetry run black .
   poetry run ruff check .
   ```

6. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance tasks

7. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking (optional but recommended)

Run before committing:
```bash
poetry run black buddyctl/
poetry run ruff check buddyctl/
```

## Testing

We aim for high test coverage. When adding features:

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=buddyctl --cov-report=html

# View coverage report
open htmlcov/index.html
```

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

When you submit code changes, your submissions are understood to be under the same [Apache 2.0 License](LICENSE) that covers the project.

### Contributor License Agreement (CLA)

By submitting a pull request, you represent that:
- You have the right to license your contribution to the project
- You grant the project a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable license
- You grant the project patent rights for your contributions (as per Apache 2.0)

## Questions?

Feel free to:
- Open an issue for questions
- Join discussions in existing issues
- Reach out to maintainers

Thank you for making BuddyCtl better! 🚀
