# Contributing to DDoS Protection Platform

Thank you for considering contributing to the DDoS Protection Platform! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please:

1. Check the [existing issues](https://github.com/i4edubd/ddos-potection/issues) to avoid duplicates
2. Collect relevant information:
   - OS and version
   - Docker version
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Error logs

Create an issue using this template:

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
 - OS: [e.g., Ubuntu 22.04]
 - Docker Version: [e.g., 24.0.0]
 - Browser: [e.g., Chrome 120]

**Additional context**
Any other context about the problem.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Create an issue and provide:

- Clear and descriptive title
- Detailed description of the proposed feature
- Explain why this enhancement would be useful
- List any alternative solutions considered
- Mock-ups or examples if applicable

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Write or update tests
5. Update documentation
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

#### Pull Request Guidelines

- Follow the existing code style
- Write clear commit messages
- Include tests for new features
- Update documentation as needed
- Keep PRs focused (one feature per PR)
- Reference any related issues
- Ensure all tests pass
- Update CHANGELOG.md

## Development Process

### Setting Up Development Environment

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

### Coding Standards

#### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions small and focused
- Use meaningful variable names

Example:
```python
def calculate_entropy(data: List[str]) -> float:
    """
    Calculate Shannon entropy of data.
    
    Args:
        data: List of string values
        
    Returns:
        Entropy value as float
    """
    # Implementation here
    pass
```

#### JavaScript (Frontend)

- Use ES6+ features
- Follow Airbnb JavaScript Style Guide
- Use functional components with hooks
- Keep components small and reusable
- Use meaningful component names

Example:
```javascript
/**
 * Alert card component
 * @param {Object} alert - Alert object with type, severity, etc.
 * @returns {JSX.Element} Alert card component
 */
function AlertCard({ alert }) {
  return (
    <div className="alert-card">
      {/* Implementation */}
    </div>
  );
}
```

### Commit Messages

Follow the conventional commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(api): add endpoint for bulk rule creation
fix(frontend): resolve dashboard refresh issue
docs(readme): update installation instructions
test(backend): add tests for anomaly detector
```

### Testing

#### Backend Tests

```bash
cd backend
pytest
```

Write tests for:
- API endpoints
- Business logic
- Database operations
- Service functions

#### Frontend Tests

```bash
cd frontend
npm test
```

Write tests for:
- Component rendering
- User interactions
- API calls
- State management

### Documentation

Update documentation when:
- Adding new features
- Changing APIs
- Modifying configuration
- Updating dependencies

Documentation locations:
- `README.md`: Project overview
- `QUICKSTART.md`: Quick start guide
- `DEPLOYMENT.md`: Deployment instructions
- `DEVELOPMENT.md`: Development guide
- `CHANGELOG.md`: Version history
- Code comments: Inline documentation

## Project Structure

```
ddos-potection/
├── backend/           # Python backend
│   ├── models/       # Database models
│   ├── routers/      # API routes
│   ├── services/     # Business logic
│   └── tests/        # Backend tests
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   └── services/    # API client
├── scripts/           # Integration scripts
├── docker/            # Docker configs
└── docs/              # Documentation
```

## Review Process

1. **Automated Checks**: CI/CD runs tests and linters
2. **Code Review**: Maintainers review code quality
3. **Testing**: Verify functionality works as expected
4. **Documentation**: Check docs are updated
5. **Approval**: At least one maintainer approves
6. **Merge**: Changes are merged to main branch

## Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create release branch
4. Test thoroughly
5. Create GitHub release
6. Deploy to production

## Getting Help

- **GitHub Issues**: Report bugs or ask questions
- **Discussions**: General questions and ideas
- **Discord**: Real-time chat (coming soon)
- **Email**: support@ispbills.com

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to making the internet safer! 🛡️

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
