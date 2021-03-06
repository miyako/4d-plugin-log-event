;   / *   S a m p l e   M e s s a g e   T e x t   F i l e 
 ;     * 
 ;     *   M e s s a g e   T e x t   F i l e s 
 ;     *   h t t p s : / / m s d n . m i c r o s o f t . c o m / e n - u s / l i b r a r y / d d 9 9 6 9 0 6 ( v = v s . 8 5 ) . a s p x 
 ;     *   R e p o r t i n g   E v e n t s 
 ;     *   h t t p s : / / m s d n . m i c r o s o f t . c o m / e n - u s / l i b r a r y / a a 3 6 3 6 8 0 ( v = v s . 8 5 ) . a s p x 
 ;     * / 
 
 ;   / /   T h i s   i s   t h e   h e a d e r   s e c t i o n . 
 
 S e v e r i t y N a m e s = ( S u c c e s s = 0 x 0 : S T A T U S _ S E V E R I T Y _ S U C C E S S 
     I n f o r m a t i o n a l = 0 x 1 : S T A T U S _ S E V E R I T Y _ I N F O R M A T I O N A L 
     W a r n i n g = 0 x 2 : S T A T U S _ S E V E R I T Y _ W A R N I N G 
     E r r o r = 0 x 3 : S T A T U S _ S E V E R I T Y _ E R R O R 
 ) 
 
 F a c i l i t y N a m e s = ( S y s t e m = 0 x 0 : F A C I L I T Y _ S Y S T E M 
     R u n t i m e = 0 x 2 : F A C I L I T Y _ R U N T I M E 
 ) 
 
 L a n g u a g e N a m e s = ( E n g l i s h = 0 x 4 0 9 : M S G 0 0 4 0 9 ) 
 L a n g u a g e N a m e s = ( J a p a n e s e = 0 x 4 1 1 : M S G 0 0 4 1 1 ) 
 
 ;   / /   T h e   f o l l o w i n g   a r e   t h e   m e s s a g e   d e f i n i t i o n s . 
 
 M e s s a g e I d T y p e d e f = W O R D 
 
 M e s s a g e I d = 0 x 1 
 S y m b o l i c N a m e = M S G _ 1 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 
 ;   / /   B a s e d   o n   o r i g i n a l   4 d m s g . d l l 
 
 M e s s a g e I d = 0 x 2 
 S y m b o l i c N a m e = M S G _ D A T A B A S E _ L O G _ S T A R T 
 L a n g u a g e = E n g l i s h 
 T h e   d a t a b a s e   % 1 ! S !   h a s   b e e n   s u c c e s s f u l l y   s t a r t e d 
 . 
 
 L a n g u a g e = J a p a n e s e 
 򹟖򠲸�0�0n0% 1 ! S ! �0嫊薡W0~0W0_0
 . 
 
 M e s s a g e I d = 0 x 3 
 S y m b o l i c N a m e = M S G _ W E B _ L O G _ S T A R T 
 L a n g u a g e = E n g l i s h 
 T h e   w e b   s e r v e r   % 1 ! S !   h a s   b e e n   s u c c e s s f u l l y   s t a r t e d 
 . 
 
 L a n g u a g e = J a p a n e s e 
 W e b 򂇦󕋎n0% 1 ! S ! �0嫊薡W0~0W0_0
 . 
 
 M e s s a g e I d = 0 x 4 
 S y m b o l i c N a m e = M S G _ W E B _ L O G _ H A L T 
 L a n g u a g e = E n g l i s h 
 T h e   w e b   s e r v e r   % 1 ! S !   h a s   b e e n   h a l t e d 
 . 
 
 L a n g u a g e = J a p a n e s e 
 W e b 򂇦󕋎n0% 1 ! S ! �0\PbkW0~0W0_0
 . 
 
 M e s s a g e I d = 0 x 5 
 S y m b o l i c N a m e = M S G _ 5 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 
 M e s s a g e I d = 0 x 6 
 S y m b o l i c N a m e = M S G _ 6 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 
 M e s s a g e I d = 0 x 7 
 S y m b o l i c N a m e = M S G _ 7 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 
 ;   / /   T h e   L O G   E V E N T   C O M M A N D 
 
 M e s s a g e I d = 0 x 8 
 S y m b o l i c N a m e = M S G _ L O G _ E V E N T 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 
 M e s s a g e I d = 0 x 9 
 S y m b o l i c N a m e = M S G _ 9 
 L a n g u a g e = E n g l i s h 
 % 1 ! S ! % 0 
 . 
 
 L a n g u a g e = J a p a n e s e 
 % 1 ! S ! % 0 
 . 
 