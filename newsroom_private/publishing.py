"""Daily news windows and one separate opinion poll; no catch-up bursts."""
from datetime import datetime,timedelta
from . import engine as e

def today_records(data,at,*,poll=False):
 return [r for r in data['history']if not r.get('test')and (r.get('kind')=='poll')==poll and r.get('status')!='failed_confirmed'and datetime.fromisoformat(r['at']).astimezone(e.MSK).date()==at.astimezone(e.MSK).date()]
def slot(at):
 local=at.astimezone(e.MSK);hours=e.CONFIG.get('posting_windows_moscow',[9,11,14,16,18,22]);due=[h for h in hours if h<=local.hour]
 return local.replace(hour=due[-1],minute=0,second=0,microsecond=0).isoformat()if due else None

def news_gate(data,at):
 local=at.astimezone(e.MSK);hours=e.CONFIG.get('posting_windows_moscow',[9,11,14,16,18,22]);records=today_records(data,at);due=[h for h in hours if h<=local.hour];key=slot(at)
 if due and len(records)<len(due)and not any(r.get('publication_slot')==key for r in records):return None
 # Existing morning posts consume the early ordinal slots when enabling mid-day.
 future=[h for i,h in enumerate(hours)if h>local.hour and i>=len(records)]
 next_at=local.replace(hour=future[0],minute=0,second=0,microsecond=0)if future else(local+timedelta(days=1)).replace(hour=hours[0],minute=0,second=0,microsecond=0)
 return {'idle':'publication_window_not_due','ordinary_posts_today':len(records),'next_window_moscow':next_at.isoformat()}

POLLS=[
 ('first-trip','Куда отправишься первым в GTA 6?',['По улицам Вайс-Сити','На острова','Исследовать болота','Покорять горы']),
 ('first-car','Какую машину ищешь первым делом в GTA 6?',['Быстрый спорткар','Внедорожник','Классическую тачку','Первую попавшуюся']),
 ('route','Что интереснее исследовать в GTA 6?',['Спрятанные места','Редкие машины','Пасхалки','Необычные встречи']),
 ('heist','Какой подход к ограблению тебе ближе?',['Долго готовиться','Импровизировать','Найти тихий путь','Главное — план побега']),
 ('bug','Заметил смешной баг. Что сделаешь?',['Запишу видео','Попробую повторить','Покажу друзьям','Продолжу прохождение']),
 ('transport','Как тебе интереснее путешествовать по миру GTA?',['За рулём','По воде','По воздуху','Пешком: больше деталей']),
 ('mission','Как проходишь новую GTA?',['Сразу по сюжету','Сначала изучаю карту','Ищу необычные находки','Чередую всё понемногу']),
 ('guide','Какой разбор сделать следующим?',['Где искать машины','Необычные места','Пасхалки и детали','Маршруты для прогулок']),
 ('driving','Что важнее в виртуальной машине?',['Скорость','Управляемость','Внешний вид','Проходимость']),
 ('wanted','Твоя первая мысль во время погони в GTA?',['Найти укрытие','Свернуть с трассы','Переехать на другую тачку','Вспомнить, где я свернул']),
 ('spoilers','Как относишься к сюжетным спойлерам?',['Вообще не открываю','Только без финала','Интересны любые детали','Сначала пройду сам']),
 ('details','Какие детали цепляют в GTA больше?',['Поведение прохожих','Физика машин','Звуки и атмосфера','Мелочи в интерьерах']),
 ('collect','Что сохранишь из наших постов?',['Карту с маршрутом','Короткую инструкцию','Видео с находкой','Подборку советов']),
 ('playstyle','Твой стиль игры в GTA?',['Осторожный исследователь','Любитель скорости','Охотник за деталями','Мастер непредсказуемости'])]

def poll_due(data,at):
 cfg=e.CONFIG.get('daily_poll',{});local=at.astimezone(e.MSK)
 if not cfg.get('enabled')or not cfg.get('hour_moscow',20)<=local.hour<cfg.get('window_end_hour_moscow',22):return False
 if today_records(data,at,poll=True):return False
 if any(r.get('status')in('pending','uncertain')for r in data['history']):return False
 sent=[r for r in data['history']if r.get('status')=='sent'and not r.get('test')]
 return not sent or at-max(datetime.fromisoformat(r['at'])for r in sent)>=timedelta(hours=e.CONFIG['minimum_gap_hours'])

def send_poll(m,state,at):
 data=m.private_data(state);cid=m.check_destination();used={r.get('poll_template')for r in data['history']if r.get('kind')=='poll'};available=[p for p in POLLS if p[0]not in used]or POLLS
 template=available[at.astimezone(e.MSK).date().toordinal()%len(available)];key,question,options=template;question+='\n\n@lesterdossier'
 record={'at':at.isoformat(),'kind':'poll','status':'pending','destination':'channel','event_key':'daily_poll_'+at.astimezone(e.MSK).date().isoformat(),'poll_template':key,'source_hashes':[],'tokens':[]}
 data['history'].append(record);state.save()
 try:
  result=m.telegram('sendPoll',{'chat_id':cid,'question':question,'options':options,'is_anonymous':True,'allows_multiple_answers':False})
  if not result.get('ok'):record['status']='failed_confirmed';state.save();raise RuntimeError('poll_rejected')
  msg=result['result']
  if not m.expected_delivery_chat(msg.get('chat',{}),cid)or not msg.get('poll'):raise RuntimeError('unexpected_poll_delivery')
  record.update(status='sent',message_id=msg['message_id'],poll_id=msg['poll']['id']);state.save()
 except Exception:
  if record['status']=='pending':record['status']='uncertain';state.save()
  raise
 return {'delivered':True,'kind':'poll','destination':'channel','message_id':record['message_id']}
