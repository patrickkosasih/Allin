import pygame.gfxdraw


def draw_rounded_rect(surface: pygame.Surface, rect: pygame.Rect,
                      color=(0, 0, 0), b_color=(0, 0, 0), b=0, r=-1) -> None:
    """
    Draw a rounded rectangle on the specified surface with the given rect.

    When the radius is set to a non-positive value, then the function draws a fully rounded rectangle, a.k.a. a stadium.

    A stadium is drawn by a rectangle and 2 antialiased circles. If the radius (r) is specified, the rounded rectangle
    is drawn using two stadiums and an additional horizontal rectangle.

    If the border thickness (b) is more than zero, the rounded rectangle would be drawn in two parts: the outer part
    (for the border) and the inner part (for the fill).

    :param surface: The Pygame surface to draw on
    :param rect: The rect that determines the position and dimensions rounded rectangle.

    :param color: The fill color of the button.
    :param b_color: The border color.

    :param b: The border thickness. If set to 0 then the border is not drawn.
    :param r: The corner radius of the rounded rectangle. If set to a non-positive value, then the function draws a
    fully rounded rectangle / stadium.
    """

    x, y, w, h = rect

    if len(color) == 4 and color[3] < 255:
        """
        If the color is translucent, an opaque rounded rectangle is drawn in a separate canvas, and then the alpha gets set
        after the rounded rectangle has been drawn.
        """
        canvas = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        *color, alpha = color
    else:
        canvas = surface
        alpha = 255

    if b > 0:
        """
        If border thickness > 0, draw two rounded rectangles (outer and inner) with b = 0.
        """
        # Outer rectangle (border)
        draw_rounded_rect(canvas, rect, b_color, b=0, r=r)

        # Inner rectangle (fill)
        inner = pygame.Surface((w, h), pygame.SRCALPHA)
        draw_rounded_rect(inner, pygame.Rect(b, b, w - 2 * b, h - 2 * b), color, b=0, r=r)
        canvas.blit(inner, rect)

    elif r == 0:
        """
        Draw a plain rectangle.
        """
        pygame.gfxdraw.box(canvas, rect, color)

    elif r < 0:
        """
        Draw a borderless stadium (fully rounded rectangle): 1 rectangle and 2 circles.
        """
        r = min(h, w) // 2

        pygame.gfxdraw.aacircle(canvas, x + r, y + r, r, color)  # Left circle
        pygame.gfxdraw.filled_circle(canvas, x + r, y + r, r, color)

        pygame.gfxdraw.aacircle(canvas, x + w - r, y + r, r, color)  # Right circle
        pygame.gfxdraw.filled_circle(canvas, x + w - r, y + r, r, color)

        pygame.gfxdraw.box(canvas, (x + r, y - 1, (w - 2 * r), h + 2), color)  # Rectangle

    else:
        """
        Draw a borderless rounded rectangle: 2 stadiums and 1 horizontal rectangle.
        """
        draw_rounded_rect(canvas, pygame.Rect(x, y, w, 2 * r), color, b=0, r=-1)  # Top rounded rectangle
        draw_rounded_rect(canvas, pygame.Rect(x, h - 2 * r, w, 2 * r), color, b=0, r=-1)  # Bottom rounded rectangle
        pygame.gfxdraw.box(canvas, (x - 1, y + r, w + 2, (h - 2 * r)), color)  # Horizontal rectangle

    if canvas is not surface:
        canvas.set_alpha(alpha)
        surface.blit(canvas, (0, 0))


def draw_circle(surface: pygame.Surface, x: int, y: int, r: int, color: tuple):
    r -= 1
    pygame.gfxdraw.aacircle(surface, x, y, r, color)
    pygame.gfxdraw.filled_circle(surface, x, y, r, color)
