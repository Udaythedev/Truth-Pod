# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- Initial project scaffold: FastAPI backend, Device SDK, CLI, Docker, CI, tests, and packaging.

## Initial commit
- FastAPI backend with device registration, trending/search, and face enroll/recognize endpoints.
- SQLModel models and Alembic scaffold.
- Device SDK (sync + async) packaged with src layout and a Click CLI.
- Dockerfile and docker-compose for Postgres + Redis.
- GitHub Actions workflows for CI, docker image build, and release automation (draft).
