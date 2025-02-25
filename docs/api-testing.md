# API Testing Guide

## Overview
This guide explains how to test the ReproSchema backend API endpoints manually.

## Prerequisites
- `curl` command-line tool
- Running ReproSchema server (via `docker compose up`)
- Initial token (found in backend logs)

## Getting Started

1. First, check the backend logs to get the initial token:


2. Get an auth token using the initial token:



3. Use the auth token to submit data:


## API Endpoints

### Health Check


### Get Auth Token

Parameters:
- `token`: Initial token from backend logs
- `project`: Project name (default: "study")
- `expiry_minutes`: Token expiry in minutes (default: 90)

### Submit Data

Headers:
- `Authorization`: Auth token from `/api/token` endpoint
- `Content-Type`: Must be `application/json`

### Get Schema


## Data Storage
Submitted responses are stored in:


## Common Issues
1. "Invalid token" error:
   - Make sure you're using the correct initial token from logs
   - Initial tokens are regenerated on container restart

2. "Invalid auth token" error:
   - Auth tokens expire after 90 minutes
   - Get a new auth token using the initial token
   - Don't include "Bearer " prefix in Authorization header

## Development Testing
For development mode features: