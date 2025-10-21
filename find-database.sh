#!/bin/bash

echo "================================================================"
echo "  DATABASE DETECTION"
echo "================================================================"
echo ""

echo "All databases:"
docker exec wardops-postgres-prod psql -U ward_admin -l 2>/dev/null

echo ""
echo "----------------------------------------------------------------"
echo "Checking for Ward databases:"
docker exec wardops-postgres-prod psql -U ward_admin -l 2>/dev/null | grep -i ward

echo ""
echo "----------------------------------------------------------------"
echo "Checking DATABASE_URL from API container:"
docker exec wardops-api-prod env | grep DATABASE_URL

echo ""
echo "================================================================"
