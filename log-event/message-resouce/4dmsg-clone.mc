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
 M e s s a g e I d T y p e d e f = D W O R D 
 
 M e s s a g e I d = 0 x 1 
 S e v e r i t y = I n f o r m a t i o n a l 
 F a c i l i t y = R u n t i m e 
 S y m b o l i c N a m e = M S G _ 1 
 L a n g u a g e = E n g l i s h 
 E v e n t : % 1 ! S ! 
 . 
 
 L a n g u a g e = J a p a n e s e 
 񍯐�0�0: % 1 ! S ! 
 . 
 