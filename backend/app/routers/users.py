import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
import bcrypt

from app import models, schemas
from app.database import get_db
from app.permissions import require_admin
from app.validators import validate_user_name

router = APIRouter(prefix="/api/users", tags=["users"])


def _order_counts(db: Session) -> dict:
    """How many OrderHistory rows mention each name -- used to sort the
    快速登入 (quick login) list so the most frequent orderers show up first."""
    rows = db.query(
        models.OrderHistoryLine.user, func.count(models.OrderHistoryLine.order_history_id.distinct())
    ).group_by(models.OrderHistoryLine.user).all()
    return {name: count for name, count in rows}


def _to_out(u: models.User, counts: dict) -> schemas.UserOut:
    return schemas.UserOut(id=u.id, name=u.name, order_count=counts.get(u.name, 0),
                            is_admin=bool(u.is_admin), ui_mode=u.ui_mode or "normal")


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    counts = _order_counts(db)
    users = db.query(models.User).all()
    out = [_to_out(u, counts) for u in users]
    out.sort(key=lambda u: (-u.order_count, u.name))
    return out


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    return _to_out(u, _order_counts(db))


@router.post("", response_model=schemas.UserOut)
def login_or_create(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    """Powers both the "登入&自動建立" free-text field and the 快速登入 list
    (which just re-submits an existing name) -- idempotent: matching an
    existing name (case-insensitive) logs in as that person instead of
    creating a duplicate roster entry."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(400, "請輸入使用者名稱")
    existing = db.query(models.User).filter(func.lower(models.User.name) == name.lower()).first()
    
    if existing:
        if existing.password_hash is None:
            if payload.password:
                existing.password_hash = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.commit()
        else:
            if not payload.password:
                raise HTTPException(400, "請輸入密碼")
                
            # Check for reset code login
            if existing.reset_code and existing.reset_code_expires_at and existing.reset_code_expires_at > dt.datetime.utcnow():
                if bcrypt.checkpw(payload.password.encode('utf-8'), existing.reset_code.encode('utf-8')):
                    existing.password_hash = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    existing.reset_code = None
                    existing.reset_code_expires_at = None
                    db.commit()
                    return _to_out(existing, _order_counts(db))
                    
            if not bcrypt.checkpw(payload.password.encode('utf-8'), existing.password_hash.encode('utf-8')):
                raise HTTPException(400, "密碼錯誤")
                
        return _to_out(existing, _order_counts(db))
        
    name = validate_user_name(name)
    u = models.User(name=name)
    if payload.password:
        u.password_hash = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.add(u)
    db.commit()
    db.refresh(u)
    return _to_out(u, _order_counts(db))


@router.patch("/{user_id}", response_model=schemas.UserOut)
def rename_user(user_id: int, payload: schemas.UserRenameIn, acting_user: str,
                 db: Session = Depends(get_db)):
    """v0.7: 管理使用者 is admin-only -- `acting_user` must be an is_admin roster entry."""
    require_admin(db, acting_user)
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    new_name = validate_user_name(payload.name)
    # v0.12: 大小寫視為同一人 -- login_or_create 早就用 func.lower() 比對過,這裡
    # 補上同樣的檢查,避免管理員把某人改名成跟別人只差大小寫的名字(例如已經有
    # "Mike Chen",又把別人改名成"mike chen"),造成兩個外觀幾乎一樣的帳號。
    dup = db.query(models.User).filter(
        func.lower(models.User.name) == new_name.lower(), models.User.id != user_id).first()
    if dup:
        raise HTTPException(400, f"已經有使用者叫「{dup.name}」(大小寫視為同一人),請改用其他名稱")
    u.name = new_name
    db.commit()
    db.refresh(u)
    return _to_out(u, _order_counts(db))


@router.patch("/{user_id}/ui-mode", response_model=schemas.UserOut)
def update_ui_mode(user_id: int, payload: schemas.UiModeIn, db: Session = Depends(get_db)):
    """v0.11: 大字模式偏好跟著帳號走,不是本機瀏覽器設定 -- 換裝置/換人登入都會套用
    最後一次選的模式。個人偏好,不用 admin 權限(誰都能改自己的)。"""
    if payload.ui_mode not in ("normal", "large"):
        raise HTTPException(400, "ui_mode 必須是 normal 或 large")
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    u.ui_mode = payload.ui_mode
    db.commit()
    db.refresh(u)
    return _to_out(u, _order_counts(db))


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, acting_user: str, db: Session = Depends(get_db)):
    """Removes this person from the roster/quick-login list only -- does NOT
    touch any orders/votes/history they're mentioned in (those store the name
    as a plain string snapshot, see the note in models.py). Admin-only (v0.7)."""
    require_admin(db, acting_user)
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(404, "User not found")
    db.delete(u)
    db.commit()
    return None

import random

@router.post("/forgot-password", status_code=200)
def forgot_password(payload: schemas.ForgotPasswordIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    email = payload.email.strip()
    if not name or not email:
        raise HTTPException(400, "請輸入帳號與Email")
        
    u = db.query(models.User).filter(func.lower(models.User.name) == name.lower()).first()
    if not u or not u.email or u.email.lower() != email.lower():
        # Do not leak whether user exists or email matches, but for usability we might want to tell them.
        # Let's tell them for better UX in this internal app.
        raise HTTPException(400, "帳號不存在或 Email 不符")
        
    code = f"{random.randint(0, 9999):04d}"
    u.reset_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    u.reset_code_expires_at = dt.datetime.utcnow() + dt.timedelta(minutes=10)
    db.commit()
    
    # 寄送 Email
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_port = os.getenv("SMTP_PORT", "465")
    
    if smtp_server and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart()
            msg["From"] = f"訂餐系統 <{smtp_user}>"
            msg["To"] = u.email
            msg["Subject"] = "【訂餐系統】忘記密碼 - 臨時驗證碼"
            
            body = f"您好 {u.name}，\n\n您的臨時登入驗證碼為：{code}\n\n請在畫面上輸入此驗證碼以完成登入並重設密碼。驗證碼將於 10 分鐘後失效。\n\n此為系統自動發送，請勿直接回覆。"
            msg.attach(MIMEText(body, "plain"))
            
            # 使用 SSL 進行安全連線
            with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
                
            print(f"\n[Email Sent] Forgot Password Code sent to {u.email}\n")
        except Exception as e:
            print(f"\n[Email Error] Failed to send to {u.email}: {e}\n")
            raise HTTPException(500, "寄件伺服器發生錯誤，無法發送驗證碼信件")
    else:
        # Fallback for local testing if no SMTP is configured
        print(f"\n[{name}] Forgot Password Code: {code}\n")
        
    return {"message": "已發送臨時密碼"}

@router.get("/me/info")
def get_my_info(name: str, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(func.lower(models.User.name) == name.lower()).first()
    if not u:
        raise HTTPException(404, "User not found")
    return {
        "email": u.email,
        "has_password": u.password_hash is not None
    }

@router.put("/me/email")
def update_email(payload: schemas.UpdateEmailIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(func.lower(models.User.name) == payload.name.lower()).first()
    if not u:
        raise HTTPException(404, "User not found")
        
    u.email = payload.email.strip()
    db.commit()
    return {"message": "Email已更新"}

@router.put("/me/password")
def update_password(payload: schemas.UpdatePasswordIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(func.lower(models.User.name) == payload.name.lower()).first()
    if not u:
        raise HTTPException(404, "User not found")
        
    if not u.email:
        raise HTTPException(400, "變更密碼前必須先設定 Email")
        
    if u.password_hash is not None:
        if not bcrypt.checkpw(payload.current_password.encode('utf-8'), u.password_hash.encode('utf-8')):
            raise HTTPException(400, "目前密碼錯誤")
            
    if payload.current_password == payload.new_password:
        raise HTTPException(400, "新舊密碼不能相同")
        
    u.password_hash = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.commit()
    return {"message": "密碼已更新"}
