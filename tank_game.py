import random
import sys
from dataclasses import dataclass

import pygame


SCREEN_WIDTH = 900
SCREEN_HEIGHT = 650
FPS = 60

PLAYER_SPEED = 4
ENEMY_SPEED = 2
BULLET_SPEED = 8
ENEMY_FIRE_CHANCE = 0.01
ENEMY_SPAWN_INTERVAL = 1800  # ms


DIRECTION_VECTORS = {
    "up": pygame.Vector2(0, -1),
    "down": pygame.Vector2(0, 1),
    "left": pygame.Vector2(-1, 0),
    "right": pygame.Vector2(1, 0),
}


@dataclass
class Colors:
    background: tuple[int, int, int] = (25, 25, 30)
    player: tuple[int, int, int] = (60, 180, 75)
    enemy: tuple[int, int, int] = (220, 70, 70)
    bullet_player: tuple[int, int, int] = (250, 230, 80)
    bullet_enemy: tuple[int, int, int] = (245, 120, 120)
    text: tuple[int, int, int] = (230, 230, 230)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos: pygame.Vector2, direction: str, is_player: bool):
        super().__init__()
        self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
        color = Colors().bullet_player if is_player else Colors().bullet_enemy
        pygame.draw.circle(self.image, color, (4, 4), 4)
        self.rect = self.image.get_rect(center=pos)
        self.velocity = DIRECTION_VECTORS[direction] * BULLET_SPEED
        self.is_player = is_player

    def update(self):
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        if (
            self.rect.right < 0
            or self.rect.left > SCREEN_WIDTH
            or self.rect.bottom < 0
            or self.rect.top > SCREEN_HEIGHT
        ):
            self.kill()


class Tank(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int, color: tuple[int, int, int], speed: int):
        super().__init__()
        self.base_image = pygame.Surface((44, 44), pygame.SRCALPHA)
        self._draw_tank(self.base_image, color)
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = speed
        self.direction = "up"
        self.last_shot = 0

    @staticmethod
    def _draw_tank(surface: pygame.Surface, color: tuple[int, int, int]):
        # 履带
        pygame.draw.rect(surface, (35, 35, 35), (4, 4, 8, 36), border_radius=2)
        pygame.draw.rect(surface, (35, 35, 35), (32, 4, 8, 36), border_radius=2)
        # 车身
        pygame.draw.rect(surface, color, (10, 8, 24, 28), border_radius=4)
        # 炮塔
        pygame.draw.circle(surface, tuple(min(255, c + 20) for c in color), (22, 22), 9)
        # 炮管（朝上）
        pygame.draw.rect(surface, (220, 220, 220), (20, 2, 4, 16), border_radius=2)

    def rotate_to_direction(self, direction: str):
        if direction == self.direction:
            return

        angle_map = {"up": 0, "right": -90, "down": 180, "left": 90}
        self.direction = direction
        center = self.rect.center
        self.image = pygame.transform.rotate(self.base_image, angle_map[direction])
        self.rect = self.image.get_rect(center=center)

    def move(self, direction: str):
        self.rotate_to_direction(direction)
        movement = DIRECTION_VECTORS[direction] * self.speed
        self.rect.x += int(movement.x)
        self.rect.y += int(movement.y)
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

    def shoot(self, bullets_group: pygame.sprite.Group, is_player: bool, cooldown_ms: int = 300):
        now = pygame.time.get_ticks()
        if now - self.last_shot >= cooldown_ms:
            self.last_shot = now
            muzzle_offset = DIRECTION_VECTORS[self.direction] * 24
            bullet_pos = pygame.Vector2(self.rect.center) + muzzle_offset
            bullets_group.add(Bullet(bullet_pos, self.direction, is_player))


class Player(Tank):
    def __init__(self):
        super().__init__(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 70, Colors().player, PLAYER_SPEED)
        self.hp = 3


class Enemy(Tank):
    def __init__(self, x: int, y: int):
        super().__init__(x, y, Colors().enemy, ENEMY_SPEED)
        self.change_dir_at = pygame.time.get_ticks() + random.randint(500, 1200)

    def update_ai(self, bullets_group: pygame.sprite.Group):
        now = pygame.time.get_ticks()

        if now >= self.change_dir_at:
            self.rotate_to_direction(random.choice(list(DIRECTION_VECTORS.keys())))
            self.change_dir_at = now + random.randint(500, 1400)

        movement = DIRECTION_VECTORS[self.direction] * self.speed
        self.rect.x += int(movement.x)
        self.rect.y += int(movement.y)

        bounds = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        if not bounds.contains(self.rect):
            self.rect.clamp_ip(bounds)
            self.rotate_to_direction(random.choice(list(DIRECTION_VECTORS.keys())))

        if random.random() < ENEMY_FIRE_CHANCE:
            self.shoot(bullets_group, is_player=False, cooldown_ms=700)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("简单坦克大战")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("simhei", 26)
        self.big_font = pygame.font.SysFont("simhei", 48)

        self.player = Player()
        self.enemies = pygame.sprite.Group()
        self.player_bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()

        self.score = 0
        self.running = True
        self.game_over = False
        self.last_spawn = 0

        for _ in range(5):
            self.spawn_enemy()

    def spawn_enemy(self):
        side = random.choice(["top", "left", "right"])
        if side == "top":
            x, y = random.randint(40, SCREEN_WIDTH - 40), random.randint(35, 80)
        elif side == "left":
            x, y = random.randint(30, 80), random.randint(70, SCREEN_HEIGHT // 2)
        else:
            x, y = random.randint(SCREEN_WIDTH - 80, SCREEN_WIDTH - 30), random.randint(70, SCREEN_HEIGHT // 2)

        enemy = Enemy(x, y)
        enemy.rotate_to_direction(random.choice(list(DIRECTION_VECTORS.keys())))
        self.enemies.add(enemy)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.player.move("up")
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.player.move("down")
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.player.move("left")
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.player.move("right")

        if keys[pygame.K_SPACE]:
            self.player.shoot(self.player_bullets, is_player=True)

    def update(self):
        if self.game_over:
            return

        self.player_bullets.update()
        self.enemy_bullets.update()

        for enemy in self.enemies:
            enemy.update_ai(self.enemy_bullets)

        # 玩家子弹打中敌人
        hits = pygame.sprite.groupcollide(self.enemies, self.player_bullets, True, True)
        if hits:
            self.score += len(hits) * 10

        # 敌人子弹打中玩家
        player_hit = pygame.sprite.spritecollide(self.player, self.enemy_bullets, dokill=True)
        if player_hit:
            self.player.hp -= len(player_hit)
            if self.player.hp <= 0:
                self.game_over = True

        # 敌人撞到玩家
        if pygame.sprite.spritecollide(self.player, self.enemies, dokill=False):
            self.game_over = True

        # 保持场上有敌人
        now = pygame.time.get_ticks()
        if now - self.last_spawn >= ENEMY_SPAWN_INTERVAL and len(self.enemies) < 8:
            self.spawn_enemy()
            self.last_spawn = now

    def draw_hud(self):
        hp_text = self.font.render(f"生命: {self.player.hp}", True, Colors().text)
        score_text = self.font.render(f"得分: {self.score}", True, Colors().text)
        help_text = self.font.render("WASD/方向键移动，空格射击，R重新开始", True, (180, 180, 180))

        self.screen.blit(hp_text, (16, 12))
        self.screen.blit(score_text, (16, 44))
        self.screen.blit(help_text, (16, SCREEN_HEIGHT - 36))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        title = self.big_font.render("游戏结束", True, (250, 120, 120))
        score = self.font.render(f"最终得分: {self.score}", True, Colors().text)
        retry = self.font.render("按 R 键重新开始 / Esc 退出", True, Colors().text)

        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)))
        self.screen.blit(score, score.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10)))
        self.screen.blit(retry, retry.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))

    def reset(self):
        self.player = Player()
        self.enemies.empty()
        self.player_bullets.empty()
        self.enemy_bullets.empty()
        self.score = 0
        self.game_over = False
        self.last_spawn = pygame.time.get_ticks()
        for _ in range(5):
            self.spawn_enemy()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif self.game_over and event.key == pygame.K_r:
                        self.reset()

            self.handle_input()
            self.update()

            self.screen.fill(Colors().background)
            self.screen.blit(self.player.image, self.player.rect)
            self.enemies.draw(self.screen)
            self.player_bullets.draw(self.screen)
            self.enemy_bullets.draw(self.screen)
            self.draw_hud()

            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    try:
        Game().run()
    except KeyboardInterrupt:
        pygame.quit()
