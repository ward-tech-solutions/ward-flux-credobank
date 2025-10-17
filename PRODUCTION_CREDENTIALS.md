# CredoBank Production Credentials

**IMPORTANT: These credentials are pre-generated for production deployment**

## 🔐 How to Use

1. Copy `.env.production` to your server
2. Rename it to `.env`:
   ```bash
   cp .env.production .env
   ```
3. The credentials are already secure and ready to use
4. **SAVE THESE CREDENTIALS SECURELY** - You'll need them to access the system

## 📋 What's Included

All these are **pre-configured** in `.env.production`:

- ✅ **Database Password** - Strong random password for PostgreSQL
- ✅ **Redis Password** - Strong random password for Redis
- ✅ **SECRET_KEY** - Cryptographically secure key for JWT tokens
- ✅ **ENCRYPTION_KEY** - Fernet encryption key for sensitive data
- ✅ **Admin Password** - Initial admin account password

## 🚀 Quick Deploy

No need to generate anything! Just:

```bash
# On Ubuntu server
git clone https://github.com/ward-tech-solutions/ward-flux-credobank.git
cd ward-flux-credobank

# Use production environment
cp .env.production .env

# Deploy
sudo docker-compose -f docker-compose.production-local.yml up -d --build
```

## 📝 Admin Login

After deployment, login with:
- **Username**: `admin`
- **Password**: Check `.env` file for `DEFAULT_ADMIN_PASSWORD` value

## ⚠️ Security Notes

- All passwords are cryptographically secure random strings
- Keys are 256-bit strength
- Change the admin password after first login
- Store these credentials in a password manager
- Never commit `.env` to Git (it's in .gitignore)

## 🔄 If You Need to Regenerate

If you want to generate new credentials:

```bash
# Generate SECRET_KEY
python3 -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

# Generate ENCRYPTION_KEY  
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate password
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then update the values in `.env` manually.

---

**Everything is ready for production deployment!** 🎉
