with open('app/routers/admin.py', 'a') as f:
    f.write('''
# --- Notifications ---
@router.get("/notifications")
async def get_notifications(admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    notifs = (await db.scalars(select(Notification).where(Notification.user_id == admin_user.id).order_by(desc(Notification.created_at)).limit(50))).all()
    return notifs

@router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, admin_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    notif = await db.scalar(select(Notification).where(Notification.id == notif_id, Notification.user_id == admin_user.id))
    if notif:
        notif.is_read = True
        await db.commit()
    return {"status": "ok"}

# --- Specific User Actions ---
@router.put("/users/{user_id}/verify")
async def verify_user(user_id: str, admin_user: User = Depends(require_roles(["super_admin"])), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    user.email_verified = not user.email_verified
    
    audit = AuditLog(admin_id=admin_user.id, action="Verify User Toggle", target_resource="User", target_id=user.id, details=f"Verified: {user.email_verified}")
    db.add(audit)
    
    await db.commit()
    return {"status": "ok", "email_verified": user.email_verified}

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, admin_user: User = Depends(require_roles(["super_admin"])), db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(404, "User not found")
    
    from app.auth import get_password_hash
    temp_password = "InsightCircle2026!"
    user.password_hash = get_password_hash(temp_password)
    
    audit = AuditLog(admin_id=admin_user.id, action="Reset Password", target_resource="User", target_id=user.id, details="Password reset to temporary password")
    db.add(audit)
    
    await db.commit()
    return {"status": "ok", "message": f"Password reset to: {temp_password}"}
''')
